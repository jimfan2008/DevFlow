# DevFlow 项目管理平台 - 前端设计文档

**版本**: V10  
**日期**: 2026-06-16  
**作者**: HouWang (后旺)  
**状态**: 修订版V10（等待后荣检验）

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
| UI 组件库 | Element Plus | 2.x | 丰富的企业级组件、主题定制 |
| Element Plus 按需引入 | unplugin-vue-components | - | 自动按需导入 Element Plus 组件 |
| HTTP 客户端 | Axios | 1.x | 拦截器、超时控制、取消请求 |
| WebSocket | 原生 WebSocket（自定义重连逻辑） | - | 实时双向通信（消息 + 流式输出统一） |
| 路由 | Vue Router | 4.x | Vue 3 官方路由 |
| 国际化 | vue-i18n | 9.x | 多语言支持 |
| 代码规范 | ESLint + Prettier | - | 统一代码风格 |
| 拖拽库 | vue-draggable-plus | 2.x | Vue3 拖拽库，支持看板拖拽排序 |
| CSS 预处理 | SCSS | - | 变量、嵌套、混入 |
| 图标库 | @element-plus/icons-vue | - | 与 Element Plus 风格统一 |
| 富文本编辑器 | @tiptap/vue-3 | - | 需求描述、文档编辑 |
| Markdown 预览 | md-editor-v3 | - | SRS 等文档预览 |
| 图表 | ECharts | 5.x | 项目进度、Agent 负载统计 |
| 虚拟列表 | vue-virtual-scroller | - | 长列表性能优化 |
| 单元测试 | Vitest | 1.x | 与 Vite 原生集成，快速测试 |
| E2E 测试 | Cypress | 13.x | 浏览器端到端测试 |
| Pinia 持久化 | pinia-plugin-persistedstate | - | 设置等状态的持久化 |

**修订说明（V9 -> V10）：**

移除 SSE（EventSource）相关技术选型，统一使用 WebSocket 处理所有实时通信场景（包括聊天消息和 Agent 流式输出）。新增虚拟列表、测试框架、Pinia 持久化插件。

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
│   │   ├── index.ts            # axios 实例配置（含拦截器）
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
│   │       ├── variables.scss  # 主题变量
│   │       ├── mixins.scss     # 样式混入
│   │       └── responsive.scss # 响应式断点混入
│   ├── components/             # 通用组件
│   │   ├── common/             # 基础组件
│   │   │   ├── AppHeader.vue   # 顶部导航
│   │   │   ├── AppSidebar.vue  # 侧边栏
│   │   │   ├── AppFooter.vue   # 底部信息
│   │   │   ├── AgentBadge.vue  # Agent 状态徽章
│   │   │   ├── StatusDot.vue   # 状态指示灯
│   │   │   └── SkipLink.vue    # 无障碍跳过链接
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
│   │   │   ├── MessageList.vue # 消息列表（虚拟滚动）
│   │   │   └── MeetingAgenda.vue # 会议议程
│   │   ├── repo/               # 代码仓库组件
│   │   │   ├── RepoCard.vue    # 仓库卡片
│   │   │   ├── CommitList.vue  # 提交列表（虚拟滚动）
│   │   │   ├── BranchList.vue  # 分支列表
│   │   │   └── PRList.vue      # PR 列表
│   │   └── qa/                 # QA 相关组件
│   │       ├── QAResultCard.vue # 检验结果卡片
│   │       ├── QAScoreChart.vue # 评分图表
│   │       └── QAProblemList.vue # 问题列表
│   ├── composables/            # 组合式函数
│   │   ├── useWebSocket.ts     # WebSocket 连接（统一实时通信）
│   │   ├── useNotification.ts  # 通知管理
│   │   └── useAuth.ts          # 认证相关
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
│   │   └── errors.ts           # 自定义错误类型
│   ├── App.vue                 # 根组件
│   └── main.ts                 # 入口文件
├── tests/                      # 测试目录
│   ├── unit/                   # 单元测试
│   │   ├── components/
│   │   ├── composables/
│   │   └── stores/
│   └── e2e/                    # E2E 测试
│       ├── spec/
│       └── support/
├── index.html
├── vite.config.ts              # Vite 配置
├── tsconfig.json               # TypeScript 配置
├── .eslintrc.cjs               # ESLint 配置
├── .prettierrc                 # Prettier 配置
├── vitest.config.ts            # Vitest 配置
├── cypress.config.ts           # Cypress 配置
└── package.json
```

**修订说明（V9 -> V10）：**

1. 移除 `composables/useSSE.ts`（统一使用 WebSocket）
2. 新增 `components/common/SkipLink.vue`（无障碍跳过链接）
3. 新增 `assets/styles/responsive.scss`（响应式设计）
4. 新增 `tests/` 目录（单元测试 + E2E 测试）
5. 新增 `vitest.config.ts` 和 `cypress.config.ts`
6. `MessageList.vue` 和 `CommitList.vue` 标注为虚拟滚动优化

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
- 登录成功后获取 access token + refresh token
- **Token 安全存储方案（V10 新增）**：
  - access token：仅存储在 Pinia 内存中，不持久化到 localStorage，页面刷新后丢失，需通过 refresh token 重新获取
  - refresh token：持久化到 localStorage（键名 `devflow_refresh_token`），用于页面刷新后自动恢复会话
  - 退出登录时同时清除 Pinia 状态和 localStorage 中的 refresh token
  - access token 通过 Axios 请求拦截器自动附加到 `Authorization` 请求头
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
- 文档区域：SRS、架构设计文档等，使用 md-editor-v3 预览
- Agent 分配情况列表

#### 2.2.5 讨论群聊天 (/projects/:id/chat)

- 左侧：讨论群列表（当前项目的多个讨论群）
- 中间：消息列表，区分用户消息和 Agent 消息
- 底部：消息输入框，支持富文本
- **Agent 流式输出通过 WebSocket 的 `agent_stream_chunk` 消息类型实现（V10 修订）**，不再使用 SSE
- 会议模式：顶部显示会议议程（MeetingAgenda 组件）

#### 2.2.6 任务看板 (/projects/:id/tasks)

- 看板列：待处理、进行中、待检验、已完成、已退回
- 任务卡片：任务标题、所属步骤、负责 Agent、优先级标签
- 支持拖拽卡片在不同列之间移动（vue-draggable-plus）
- 点击任务卡片弹出任务详情抽屉

#### 2.2.7 QA 检验 (/projects/:id/qa)

- 检验结果列表，按步骤排序
- 每个检验结果展示：步骤名称、检验 Agent（后荣）、评分、状态（通过/不通过）
- 不通过的检验项展示具体问题列表（QAProblemList 组件）
- 评分雷达图（QAScoreChart 组件，基于 ECharts）

#### 2.2.8 代码仓库 (/projects/:id/repo)

- 仓库基本信息：名称、描述、默认分支
- 提交记录列表（CommitList 组件），支持分页和虚拟滚动
- 分支列表（BranchList 组件）
- PR 列表（PRList 组件），展示 PR 状态、评论数、文件变更

#### 2.2.9 系统设置 (/settings)

- 个人信息：头像、用户名
- 通知偏好：邮件通知、浏览器推送开关
- 语言切换：中文/英文
- 主题设置：浅色/深色

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

#### 3.1.5 SkipLink（无障碍跳过链接）

```typescript
// src/components/common/SkipLink.vue
<template>
  <a class="skip-link" href="#main-content">
    跳到主要内容
  </a>
</template>

<style scoped>
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #409eff;
  color: #fff;
  padding: 8px 16px;
  z-index: 9999;
  transition: top 0.3s;
}
.skip-link:focus {
  top: 0;
}
</style>
```

- 默认隐藏在视口外
- 获得键盘焦点时显示
- 点击后焦点跳转到 `#main-content` 区域

### 3.2 聊天相关组件

#### 3.2.1 ChatWindow（聊天窗口）

```typescript
interface ChatWindowProps {
  groupId: string;
  projectId: string;
}
```

- 集成 MessageList、MessageInput 子组件
- 连接 WebSocket 获取实时消息和 Agent 流式输出（V10 修订：统一使用 WebSocket）
- 自动滚动到底部
- 会议模式下显示 MeetingAgenda
- WebSocket 事件监听：
  - `chat_message`: 新消息到达
  - `agent_stream_chunk`: Agent 流式输出增量
  - `agent_stream_done`: Agent 流式输出完成
  - `message_deleted`: 消息删除通知

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
- 无障碍：Agent 消息使用 `role="listitem"`，用户消息使用 `aria-label="我的消息"`

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
- 无障碍：输入框关联 `aria-label="消息输入"`，发送按钮 `aria-label="发送消息"`

#### 3.2.4 MessageList（消息列表）

```typescript
interface MessageListProps {
  messages: GroupMessage[];
  streamingMessages: Map<string, string>;
}
```

- **虚拟滚动渲染（V10 明确方案）**：使用 `vue-virtual-scroller` 的 `RecycleScroller` 组件，当消息数量超过 50 条时启用虚拟滚动，每次渲染可见区域 ±10 条消息
- 按时间分组显示（今天、昨天、更早）
- 流式消息实时追加渲染
- 无障碍：容器使用 `role="log"` 和 `aria-live="polite"`，新消息到达时屏幕阅读器自动播报
- 性能：消息列表 DOM 节点数量控制在 100 个以内，无论消息总量多少

```vue
<!-- MessageList.vue 虚拟滚动示例 -->
<template>
  <RecycleScroller
    class="message-scroller"
    :items="messages"
    :item-size="80"
    key-field="id"
    v-slot="{ item }"
  >
    <MessageBubble :message="item" />
  </RecycleScroller>
</template>

<script setup lang="ts">
import { RecycleScroller } from 'vue-virtual-scroller';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
</script>
```

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
- 无障碍：列使用 `role="region"` 和 `aria-label`，拖拽时 `aria-grabbed="true"`，放置目标 `aria-dropeffect="move"`

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

### 4.1 userStore

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
      // 持久化 refresh token 到 localStorage
      localStorage.setItem('devflow_refresh_token', res.data.refresh_token);
    },
    async refreshToken() {
      const storedRefresh = this.refreshToken || localStorage.getItem('devflow_refresh_token');
      if (!storedRefresh) return false;
      this.refreshToken = storedRefresh;
      try {
        const res = await api.post('/auth/refresh', {
          refresh_token: storedRefresh,
        });
        this.accessToken = res.data.access_token;
        this.refreshToken = res.data.refresh_token;
        this.tokenExpiry = Date.now() + res.data.expires_in * 1000;
        // 更新持久化的 refresh token
        localStorage.setItem('devflow_refresh_token', res.data.refresh_token);
        return true;
      } catch {
        this.logout();
        return false;
      }
    },
    async restoreSession() {
      // 页面刷新后从 localStorage 恢复会话
      const storedRefresh = localStorage.getItem('devflow_refresh_token');
      if (storedRefresh) {
        return await this.refreshToken();
      }
      return false;
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
      // 清除 localStorage 中的 refresh token
      localStorage.removeItem('devflow_refresh_token');
    },
  },
});
```

**Token 安全存储方案（V10 明确）：**

| Token 类型 | 存储位置 | 生命周期 | 用途 |
|-----------|---------|---------|------|
| access token | Pinia 内存 | 单次会话，页面刷新丢失 | 附加到 HTTP 请求的 Authorization 头 |
| refresh token | localStorage (`devflow_refresh_token`) | 直到用户退出登录 | 页面刷新后恢复会话，过期时刷新 access token |

**安全设计要点：**

1. access token 不持久化到 localStorage，避免页面被 XSS 攻击时窃取长期有效的 token
2. refresh token 持久化到 localStorage，用于页面刷新后自动恢复会话
3. 退出登录时同时清除 Pinia 状态和 localStorage 中的 refresh token
4. refresh token 刷新失败时自动清除并跳转登录页

**Token 刷新机制说明：**

1. 登录成功后同时获取 access token 和 refresh token
2. access token 存储在 Pinia 内存中，refresh token 持久化到 localStorage
3. Axios 请求拦截器中检查 token 有效期：
   - 若 token 将在 60 秒内过期，主动调用 `/auth/refresh` 刷新
   - 若接口返回 401，尝试使用 refresh token 刷新
   - 刷新成功后重试原请求
   - 刷新失败则跳转登录页
4. 同一时刻只允许一个 refresh 请求，其他请求排队等待

```typescript
// axios 拦截器中的 token 刷新逻辑
let isRefreshing = false;
let failedQueue: Array<{ resolve: () => void; reject: () => void }> = [];

const processQueue = (error: null, token: string | null) => {
  failedQueue.forEach(prom => {
    if (error) prom.reject();
    else prom.resolve();
  });
  failedQueue = [];
};

axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retried) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => axios(originalRequest));
      }
      originalRequest._retried = true;
      isRefreshing = true;
      try {
        const userStore = useUserStore();
        await userStore.refreshToken();
        originalRequest.headers.Authorization = `Bearer ${userStore.accessToken}`;
        processQueue(null, userStore.accessToken);
        return axios(originalRequest);
      } catch (err) {
        processQueue(err, null);
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
```

### 4.2 projectStore

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

### 4.3 taskStore

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

### 4.4 chatStore

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
    appendStreamingContent(messageId: string, chunk: string) {
      const current = this.streamingContent.get(messageId) || '';
      this.streamingContent.set(messageId, current + chunk);
    },
    finalizeStreamingContent(messageId: string, fullContent: string) {
      const msg = this.messages.find(m => m.id === messageId);
      if (msg) msg.content = fullContent;
      this.streamingContent.delete(messageId);
    },
    connectWebSocket(groupId: string) {
      useWebSocket().connect(groupId);
    },
    disconnectWebSocket() {
      useWebSocket().disconnect();
    },
  },
});
```

**修订说明（V9 -> V10）：**

- 移除 `startSSEStream` 和 `stopSSEStream` 方法，Agent 流式输出统一通过 WebSocket 处理
- 新增 `appendStreamingContent` 方法用于 WebSocket 推送的流式增量追加
- 新增 `finalizeStreamingContent` 方法用于流式输出完成后的最终处理
- `connectWebSocket` / `disconnectWebSocket`：chatStore 委托 useWebSocket composable 处理底层 WebSocket 连接生命周期
- composable 负责连接管理，Store 负责状态更新和消息协调

**WebSocket 处理流式输出的流程：**

```
用户发送消息
  -> 后端创建消息记录，返回 messageId
  -> WebSocket 推送 agent_stream_start { messageId, agentId }
  -> chatStore.setStreamingContent(messageId, '')
  -> WebSocket 推送 agent_stream_chunk { messageId, chunk: "正在" }
  -> chatStore.appendStreamingContent(messageId, "正在")
  -> WebSocket 推送 agent_stream_chunk { messageId, chunk: "分析" }
  -> chatStore.appendStreamingContent(messageId, "分析")
  -> WebSocket 推送 agent_stream_done { messageId, fullContent: "正在分析..." }
  -> chatStore.finalizeStreamingContent(messageId, "正在分析...")
```

### 4.5 notificationStore

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

### 4.6 settingStore

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
  persist: true,
});
```

---

## 5. API 层设计

### 5.1 Axios 实例配置

**修订说明（V9 -> V10）：**

V9 仅有简单的 axios 实例创建和请求拦截器，V10 补充完整的响应拦截器、统一错误处理、请求取消机制、重试机制。

```typescript
// src/api/index.ts
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';

export interface APIError {
  code: string;
  message: string;
  status: number;
  details?: Record<string, string[]>;
}

class APIError extends Error {
  code: string;
  status: number;
  details?: Record<string, string[]>;

  constructor(data: APIError) {
    super(data.message);
    this.name = 'APIError';
    this.code = data.code;
    this.status = data.status;
    this.details = data.details;
  }
}

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const userStore = useUserStore();
    if (userStore.accessToken) {
      config.headers.Authorization = `Bearer ${userStore.accessToken}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retried?: boolean };

    // 401 统一处理：token 刷新
    if (error.response?.status === 401 && !originalRequest?._retried) {
      if (originalRequest) originalRequest._retried = true;
      const userStore = useUserStore();
      const refreshed = await userStore.refreshToken();
      if (refreshed && originalRequest) {
        originalRequest.headers.Authorization = `Bearer ${userStore.accessToken}`;
        return api(originalRequest);
      }
      userStore.logout();
      router.push('/login');
      return Promise.reject(new APIError({
        code: 'UNAUTHORIZED',
        message: '登录已过期，请重新登录',
        status: 401,
      }));
    }

    // 422 验证错误：提取字段级错误信息
    if (error.response?.status === 422) {
      const data = error.response.data as { errors?: Record<string, string[]> };
      throw new APIError({
        code: 'VALIDATION_ERROR',
        message: '输入数据验证失败',
        status: 422,
        details: data.errors,
      });
    }

    // 5xx 服务器错误：自动重试一次
    if (error.response?.status && error.response.status >= 500 && !originalRequest?._retried) {
      if (originalRequest) originalRequest._retried = true;
      return api(originalRequest);
    }

    // 超时错误
    if (error.code === 'ECONNABORTED') {
      throw new APIError({
        code: 'TIMEOUT',
        message: '请求超时，请检查网络连接',
        status: 0,
      });
    }

    // 网络错误
    if (!error.response) {
      throw new APIError({
        code: 'NETWORK_ERROR',
        message: '网络连接失败，请检查网络设置',
        status: 0,
      });
    }

    // 其他 HTTP 错误
    throw new APIError({
      code: `HTTP_${error.response?.status}`,
      message: error.response?.data as string || '请求失败',
      status: error.response?.status || 500,
    });
  }
);

export { api, APIError };
```

### 5.2 请求取消机制

```typescript
// src/api/utils.ts
import { CancelTokenSource } from 'axios';

// 管理正在进行的请求，支持取消重复请求
const pendingRequests = new Map<string, CancelTokenSource>();

export function getCancelToken(url: string): CancelTokenSource['token'] | null {
  // 取消相同 URL 的未完成请求
  const existing = pendingRequests.get(url);
  if (existing) {
    existing.cancel('被新请求替代');
  }

  const source = axios.CancelToken.source();
  pendingRequests.set(url, source);

  return source.token;
}

export function clearCancelToken(url: string) {
  pendingRequests.delete(url);
}
```

使用方式：
```typescript
// 在业务 API 中使用
export function fetchProjects() {
  const token = getCancelToken('/api/projects');
  return api.get('/projects', { cancelToken: token || undefined }).finally(() => {
    clearCancelToken('/api/projects');
  });
}
```

### 5.3 统一错误处理工具

```typescript
// src/utils/errors.ts
import { APIError } from '@/api';

export function formatAPIError(error: APIError): string {
  if (error.details) {
    const fieldErrors = Object.entries(error.details)
      .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
      .join('; ');
    return `${error.message} (${fieldErrors})`;
  }
  return error.message;
}

export function isAPIError(error: unknown): error is APIError {
  return error instanceof APIError;
}

export function isValidationError(error: APIError): boolean {
  return error.code === 'VALIDATION_ERROR';
}
```

### 5.4 API 端点清单

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

**修订说明（V9 -> V10）：** 移除 SSE 流式输出端点（`GET /groups/:id/messages/:id/stream`），流式输出统一通过 WebSocket 推送。

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

---

## 6. WebSocket 通信设计（统一实时通信）

**修订说明（V9 -> V10）：**

V9 同时使用 WebSocket 和 SSE 两种协议，存在职责重叠和连接管理复杂度高的问题。V10 统一使用 WebSocket 处理所有实时通信场景，通过消息类型区分不同用途。Agent 流式输出作为 WebSocket 的一种消息类型（`agent_stream_chunk`）处理，不再需要单独的 SSE 连接和 EventSource。

**优势：**

1. 只需维护一个 WebSocket 连接，降低连接管理复杂度
2. 重连逻辑统一，无需分别处理 WebSocket 和 SSE 的重连
3. 前后端实现更简洁，减少维护成本
4. 双向通信能力完整保留，支持客户端发送消息和服务端推送

### 6.1 WebSocket 消息类型定义

```typescript
// 服务端 -> 客户端消息类型
export type ServerMessage =
  | ChatMessageEvent
  | AgentStreamStartEvent
  | AgentStreamChunkEvent
  | AgentStreamDoneEvent
  | MessageDeletedEvent
  | AgentStatusEvent
  | TaskUpdatedEvent
  | ProjectStepChangedEvent
  | NotificationEvent;

// 客户端 -> 服务端消息类型
export type ClientMessage =
  | ChatJoinEvent
  | ChatLeaveEvent
  | SendMessageEvent;

// --- 服务端消息 ---

export interface ChatMessageEvent {
  type: 'chat_message';
  payload: GroupMessage;
}

export interface AgentStreamStartEvent {
  type: 'agent_stream_start';
  payload: {
    message_id: string;
    agent_id: string;
    agent_name: string;
  };
}

export interface AgentStreamChunkEvent {
  type: 'agent_stream_chunk';
  payload: {
    message_id: string;
    chunk: string;
  };
}

export interface AgentStreamDoneEvent {
  type: 'agent_stream_done';
  payload: {
    message_id: string;
    full_content: string;
  };
}

export interface MessageDeletedEvent {
  type: 'message_deleted';
  payload: {
    message_id: string;
  };
}

export interface AgentStatusEvent {
  type: 'agent_status';
  payload: {
    agent_id: string;
    status: 'idle' | 'working' | 'offline' | 'error';
    current_task?: string;
  };
}

export interface TaskUpdatedEvent {
  type: 'task_updated';
  payload: Task;
}

export interface ProjectStepChangedEvent {
  type: 'project_step_changed';
  payload: {
    project_id: string;
    current_step: number;
    step_name: string;
  };
}

export interface NotificationEvent {
  type: 'notification';
  payload: Notification;
}

// --- 客户端消息 ---

export interface ChatJoinEvent {
  type: 'chat.join';
  payload: {
    group_id: string;
  };
}

export interface ChatLeaveEvent {
  type: 'chat.leave';
  payload: {
    group_id: string;
  };
}

export interface SendMessageEvent {
  type: 'message.send';
  payload: {
    group_id: string;
    content: string;
  };
}
```

### 6.2 WebSocket 连接管理（useWebSocket composable）

```typescript
// src/composables/useWebSocket.ts
import { ref, onUnmounted } from 'vue';
import type { ServerMessage, ClientMessage } from '@/api/chat';

interface WebSocketOptions {
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

export function useWebSocket(options: WebSocketOptions = {}) {
  const {
    maxReconnectAttempts = 5,
    reconnectDelay = 1000,
  } = options;

  const ws = ref<WebSocket | null>(null);
  const connected = ref(false);
  const reconnectAttempts = ref(0);
  const currentGroupId = ref<string | null>(null);

  let eventHandlers: Map<string, Function[]> = new Map();
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const getWsUrl = (): string => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || location.host;
    return `${protocol}//${host}/ws`;
  };

  const connect = (groupId?: string) => {
    if (ws.value) return;

    const userStore = useUserStore();
    const token = userStore.accessToken;
    if (!token) return;

    ws.value = new WebSocket(`${getWsUrl()}?token=${token}`);

    ws.value.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
      if (groupId) {
        currentGroupId.value = groupId;
        ws.value?.send(JSON.stringify({
          type: 'chat.join',
          payload: { group_id: groupId },
        } as ChatJoinEvent));
      }
    };

    ws.value.onmessage = (event: MessageEvent) => {
      const data: ServerMessage = JSON.parse(event.data);
      triggerEvent(data.type, data);
    };

    ws.value.onerror = () => {
      // 连接错误，准备重连
    };

    ws.value.onclose = (event: CloseEvent) => {
      connected.value = false;
      ws.value = null;
      if (!event.wasClean) {
        attemptReconnect(currentGroupId.value);
      }
    };
  };

  const disconnect = () => {
    if (currentGroupId.value) {
      ws.value?.send(JSON.stringify({
        type: 'chat.leave',
        payload: { group_id: currentGroupId.value },
      } as ChatLeaveEvent));
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws.value) {
      ws.value.close(1000, 'Client disconnecting');
      ws.value = null;
      connected.value = false;
    }
    currentGroupId.value = null;
  };

  const attemptReconnect = (groupId?: string | null) => {
    const delay = Math.min(
      reconnectDelay * Math.pow(2, reconnectAttempts.value),
      30000
    );
    reconnectAttempts.value++;
    if (reconnectAttempts.value <= maxReconnectAttempts) {
      reconnectTimer = setTimeout(() => {
        if (groupId) connect(groupId);
        else connect();
      }, delay);
    } else {
      // 超过最大重连次数，通知用户
      triggerEvent('ws.max_reconnect', { attempts: reconnectAttempts.value });
    }
  };

  const send = (message: ClientMessage) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message));
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

  // 组件卸载时自动断开
  onUnmounted(() => {
    disconnect();
  });

  return {
    ws,
    connected,
    reconnectAttempts,
    connect,
    disconnect,
    send,
    on,
    off,
  };
}
```

**重连机制：**

- 最大重连次数：5 次
- 指数退避：1s -> 2s -> 4s -> 8s -> 16s（上限 30s）
- 重连成功后重置计数器
- 超过最大次数后停止重连，触发 `ws.max_reconnect` 事件通知用户
- WebSocket URL 携带 access token 进行认证
- 组件卸载时自动断开连接和清除重连定时器

### 6.3 ChatView 中 WebSocket 使用方式

```vue
<!-- ChatView.vue -->
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { useChatStore } from '@/stores/chatStore';
import { useWebSocket } from '@/composables/useWebSocket';

const chatStore = useChatStore();
const ws = useWebSocket();

onMounted(() => {
  const groupId = props.groupId;
  chatStore.connectWebSocket(groupId);

  // 监听各类 WebSocket 事件
  ws.on('chat_message', (data) => {
    chatStore.messages.push(data.payload);
  });

  ws.on('agent_stream_start', (data) => {
    chatStore.setStreamingContent(data.payload.message_id, '');
  });

  ws.on('agent_stream_chunk', (data) => {
    chatStore.appendStreamingContent(
      data.payload.message_id,
      data.payload.chunk
    );
  });

  ws.on('agent_stream_done', (data) => {
    chatStore.finalizeStreamingContent(
      data.payload.message_id,
      data.payload.full_content
    );
  });

  ws.on('message_deleted', (data) => {
    const idx = chatStore.messages.findIndex(
      m => m.id === data.payload.message_id
    );
    if (idx > -1) chatStore.messages.splice(idx, 1);
  });

  ws.on('ws.max_reconnect', () => {
    ElMessage.warning('WebSocket 连接断开，请刷新页面重试');
  });
});

onUnmounted(() => {
  chatStore.disconnectWebSocket();
});
</script>
```

### 6.4 多 Agent 同时回复场景

讨论群中若多个 Agent 同时回复用户，每个回复拥有独立的 messageId，WebSocket 按 messageId 区分：

```
用户发送消息 "请分析需求"
  -> Agent A 开始回复 (messageId: msg-001)
     WS推送: agent_stream_start { message_id: "msg-001", agent_id: "agent-a" }
  -> Agent B 开始回复 (messageId: msg-002)
     WS推送: agent_stream_start { message_id: "msg-002", agent_id: "agent-b" }
  -> Agent A 推送增量
     WS推送: agent_stream_chunk { message_id: "msg-001", chunk: "需求分析..." }
  -> Agent B 推送增量
     WS推送: agent_stream_chunk { message_id: "msg-002", chunk: "从架构角度看..." }
  -> Agent A 回复完成
     WS推送: agent_stream_done { message_id: "msg-001", full_content: "..." }
  -> Agent B 回复完成
     WS推送: agent_stream_done { message_id: "msg-002", full_content: "..." }
```

所有消息通过同一个 WebSocket 连接推送，按 messageId 区分不同 Agent 的流式输出，互不干扰。

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
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
  },
];
```

**修订说明（V9 -> V10）：**

- 所有子路由均已使用 `() => import()` 懒加载语法，实现路由级别的代码分割
- 新增 404 通配路由

### 7.2 路由守卫

```typescript
// src/router/guards.ts
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore();

  // 需要认证的路由
  if (to.meta.requiresAuth !== false) {
    if (userStore.accessToken) {
      // 已有 token，检查是否即将过期
      const authenticated = await userStore.ensureAuthenticated();
      if (!authenticated) {
        // token 过期且刷新失败
        next({ name: 'Login', query: { redirect: to.fullPath } });
        return;
      }
    } else {
      // 无 token，尝试从 localStorage 恢复会话
      const restored = await userStore.restoreSession();
      if (!restored) {
        next({ name: 'Login', query: { redirect: to.fullPath } });
        return;
      }
    }
  }

  // 已登录用户访问登录页，重定向到仪表板
  if (to.name === 'Login' && userStore.accessToken) {
    next({ name: 'Dashboard' });
    return;
  }

  next();
});
```

**修订说明（V9 -> V10）：**

- 路由守卫中增加 `restoreSession()` 调用：用户刷新页面时，自动从 localStorage 中的 refresh token 恢复会话
- `ensureAuthenticated()` 在每次导航前检查 token 有效期，即将过期时主动刷新

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
  },
  "accessibility": {
    "skipToContent": "跳到主要内容",
    "menuToggle": "切换导航菜单",
    "sendMessage": "发送消息",
    "messageInput": "消息输入",
    "notificationBell": "通知",
    "userMenu": "用户菜单"
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

**修订说明（V9 -> V10）：** 语言包中新增 `accessibility` 命名空间，包含无障碍相关文本的国际化键值。

---

## 9. 样式设计

### 9.1 主题变量

```scss
// src/assets/styles/variables.scss
$primary-color: #409eff;
$success-color: #67c23a;
$warning-color: #e6a23c;
$danger-color: #f56c6c;
$info-color: #909399;

$bg-color: #f5f7fa;
$card-bg: #ffffff;
$text-primary: #303133;
$text-secondary: #606266;
$text-muted: #909399;

$border-color: #dcdfe6;
$border-radius: 8px;

$sidebar-width: 240px;
$sidebar-collapsed-width: 64px;
$header-height: 56px;
```

### 9.2 深色主题

```scss
// 通过 Element Plus 主题切换
// dark 模式下覆盖变量
$dark-bg-color: #141414;
$dark-card-bg: #1d1e1f;
$dark-text-primary: #e5eaf3;
$dark-text-secondary: #c0c4cc;
```

### 9.3 响应式设计（V10 新增）

```scss
// src/assets/styles/responsive.scss
// 断点定义
$breakpoint-sm: 576px;   // 手机
$breakpoint-md: 768px;   // 平板
$breakpoint-lg: 992px;   // 小桌面
$breakpoint-xl: 1200px;  // 大桌面

// 响应式混入
@mixin respond-to($breakpoint) {
  @if $breakpoint == sm {
    @media (max-width: $breakpoint-sm) { @content; }
  } @else if $breakpoint == md {
    @media (max-width: $breakpoint-md) { @content; }
  } @else if $breakpoint == lg {
    @media (max-width: $breakpoint-lg) { @content; }
  } @else if $breakpoint == xl {
    @media (max-width: $breakpoint-xl) { @content; }
  }
}

// 响应式工具类
.layout-sidebar {
  width: $sidebar-width;
  @include respond-to(md) {
    position: fixed;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.3s;
    &.open { transform: translateX(0); }
  }
}

.layout-content {
  margin-left: $sidebar-width;
  @include respond-to(md) {
    margin-left: 0;
  }
}

// 聊天页面响应式
.chat-container {
  display: grid;
  grid-template-columns: 250px 1fr;
  @include respond-to(lg) {
    grid-template-columns: 1fr;
    .chat-group-list {
      display: none;
      &.mobile-open { display: block; }
    }
  }
}

// 任务看板响应式
.task-kanban {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  @include respond-to(lg) {
    grid-template-columns: repeat(3, 1fr);
  }
  @include respond-to(md) {
    grid-template-columns: 1fr;
    overflow-x: auto;
  }
}

// 项目卡片响应式
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  @include respond-to(sm) {
    grid-template-columns: 1fr;
  }
}
```

**响应式策略说明：**

| 断点 | 设备 | 适配策略 |
|------|------|---------|
| < 576px (sm) | 手机 | 单列布局，侧边栏隐藏为抽屉模式，卡片单列 |
| 576-768px | 大手机 | 同上 |
| 768-992px (md) | 平板 | 侧边栏抽屉模式，看板 3 列，聊天单列 |
| 992-1200px (lg) | 小桌面 | 侧边栏固定，看板 5 列，聊天双列 |
| > 1200px (xl) | 大桌面 | 完整布局 |

**移动端适配要点：**

1. 侧边栏：平板及以下转为抽屉式，通过汉堡菜单按钮触发
2. 聊天页面：平板及以下讨论群列表隐藏，通过按钮切换显示
3. 任务看板：平板及以下改为单列垂直滚动，或横向滚动
4. 项目卡片：手机单列，桌面自动填充
5. 触摸友好：所有点击目标最小 44x44px

---

## 10. 无障碍设计（WCAG 2.1 AA）

**修订说明（V9 -> V10）：**

V9 仅列举了无障碍要求的高层原则，V10 补充具体实现方案、代码示例和验证方法。

### 10.1 键盘导航

**实现方案：**

1. **Tab 顺序**：所有交互元素（按钮、链接、输入框、下拉菜单）可通过 Tab 键依次访问，Tab 顺序遵循视觉阅读顺序（从左到右、从上到下）

2. **焦点样式**：所有可聚焦元素具有清晰的焦点指示器，满足 2:1 的焦点对比度要求
   ```scss
   // 全局焦点样式
   *:focus-visible {
     outline: 2px solid $primary-color;
     outline-offset: 2px;
   }

   // 按钮焦点样式
   .el-button:focus-visible {
     box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.5);
   }
   ```

3. **跳过导航链接**：SkipLink 组件位于页面最顶部，是 Tab 顺序中的第一个元素，点击后将焦点跳转到 `#main-content` 区域

4. **键盘快捷键**：
   - Enter：确认、发送消息
   - Escape：关闭弹窗、抽屉
   - Arrow Up/Down：在列表、下拉菜单中导航
   - Tab：切换到下一个可聚焦元素
   - Shift+Tab：切换到上一个可聚焦元素

5. **焦点管理**：
   - 弹窗/抽屉打开时，焦点自动转移到弹窗内的第一个可交互元素
   - 弹窗/抽屉关闭时，焦点返回到打开前的元素
   - 路由切换后，焦点转移到新页面的主标题或主要内容区域
   ```typescript
   // 路由切换后焦点管理
   router.afterEach((to) => {
     const mainHeading = document.querySelector('h1, [role="main"]');
     if (mainHeading) {
       (mainHeading as HTMLElement).tabIndex = -1;
       (mainHeading as HTMLElement).focus();
     }
   });
   ```

### 10.2 ARIA 属性规范

**通用 ARIA 属性使用规范：**

| 场景 | ARIA 属性 | 示例 |
|------|----------|------|
| 图标按钮 | `aria-label` | `<el-button :icon="Bell" aria-label="通知" />` |
| 状态标签 | `aria-label` | `<el-tag aria-label="任务状态：进行中">进行中</el-tag>` |
| 消息列表 | `role="log"`, `aria-live="polite"` | `<div role="log" aria-live="polite" aria-label="聊天消息">` |
| 通知计数 | `aria-label` | `<el-badge :value="5" aria-label="5 条未读通知" />` |
| 侧边栏 | `role="navigation"`, `aria-label` | `<nav role="navigation" aria-label="主导航">` |
| 下拉菜单 | `aria-expanded`, `aria-haspopup` | `<button aria-expanded="false" aria-haspopup="true">` |
| 加载状态 | `aria-busy="true"` | `<div aria-busy="true" aria-label="加载任务列表">` |
| 表单错误 | `aria-invalid`, `aria-describedby` | `<input aria-invalid="true" aria-describedby="name-error" />` |
| 拖拽区域 | `aria-grabbed`, `aria-dropeffect` | `<div aria-grabbed="false" aria-dropeffect="move">` |
| 实时区域 | `aria-live` | `aria-live="polite"`（非紧急更新），`aria-live="assertive"`（紧急更新） |

**聊天消息无障碍实现：**
```vue
<!-- MessageList.vue -->
<template>
  <div
    role="log"
    aria-live="polite"
    aria-label="聊天消息列表"
    ref="messageContainer"
  >
    <!-- 消息项 -->
  </div>
</template>
```

```vue
<!-- MessageBubble.vue -->
<template>
  <div
    :role="message.sender_type === 'user' ? 'group' : 'article'"
    :aria-label="`${message.sender_name} 的消息，${formatTime(message.timestamp)}`"
    :class="{ 'user-message': message.sender_type === 'user' }"
  >
    <MessageContent :content="message.content" />
  </div>
</template>
```

### 10.3 色彩对比度

**WCAG 2.1 AA 级对比度要求：**

| 元素类型 | 最低对比度 | 实际设计值 |
|---------|-----------|-----------|
| 正文文本（< 18px） | 4.5:1 | $text-primary(#303133) 在白色背景上 = 12.6:1 |
| 大文本（>= 24px 或 18px 加粗） | 3:1 | $primary-color(#409eff) 在白色背景上 = 4.5:1 |
| UI 组件和图形边界 | 3:1 | $border-color(#dcdfe6) 在白色背景上 = 2.8:1（需加深） |
| 焦点指示器 | 2:1 | 2px solid #409eff 在白色背景上 = 4.5:1 |

**不单独依赖颜色传达信息的实现：**

```vue
<!-- 任务优先级标签：颜色 + 文字 -->
<template>
  <el-tag
    :type="priorityType"
    aria-label="优先级：{{ priorityLabel }}"
  >
    <el-icon :component="priorityIcon" />
    {{ priorityLabel }}
  </el-tag>
</template>

<!-- Agent 状态：圆点颜色 + 文字 -->
<template>
  <StatusDot :status="status" />
  <span>{{ statusLabel }}</span>
</template>
```

**对比度验证方法：**

使用浏览器开发者工具的 Coverage 面板或 axe DevTools 扩展验证颜色对比度，确保所有文本和图形元素满足 WCAG 2.1 AA 标准。

### 10.4 表单无障碍

**实现方案：**

1. **标签关联**：所有输入框使用 `<label for="id">` 关联，或通过 `aria-label` / `aria-labelledby` 标注
   ```vue
   <el-form-item label="用户名">
     <el-input
       v-model="form.username"
       id="username"
       aria-required="true"
       aria-invalid="false"
       aria-describedby="username-error"
     />
     <div id="username-error" role="alert" v-if="errors.username">
       {{ errors.username }}
     </div>
   </el-form-item>
   ```

2. **错误提示**：使用 `aria-invalid="true"` 标记错误字段，使用 `aria-describedby` 关联错误信息，错误信息区域使用 `role="alert"` 确保屏幕阅读器自动播报

3. **必填字段**：`aria-required="true"` + 视觉星号标记

4. **Element Plus 表单无障碍增强**：
   ```typescript
   // 全局 Element Plus 表单无障碍配置
   import { ElForm } from 'element-plus';

   // 确保 el-form-item 的 label 正确关联到输入控件
   // Element Plus 2.x 已内置 aria-label 支持
   ```

### 10.5 屏幕阅读器支持

**动态内容更新：**

1. 聊天消息到达：`aria-live="polite"` 区域自动播报新消息
2. 通知到达：`aria-live="assertive"` 区域播报紧急通知
3. 任务状态变更：使用 `role="status"` 播报状态变化
4. WebSocket 重连失败：`role="alert"` 播报连接断开警告

**Element Plus 组件无障碍增强：**

| 组件 | 增强方式 |
|------|---------|
| el-dialog | 设置 `aria-modal="true"`，管理焦点陷阱 |
| el-drawer | 设置 `aria-modal="true"`，关闭后恢复焦点 |
| el-table | 设置 `aria-label` 描述表格内容 |
| el-select | 确保 `aria-expanded` 随展开状态更新 |
| el-pagination | 设置 `aria-label="分页导航"` |
| el-tabs | Element Plus 已内置 ARIA 支持 |

### 10.6 无障碍验证清单

| 验证项 | 验证方法 | 通过标准 |
|--------|---------|---------|
| 键盘可访问性 | 仅使用键盘操作所有功能 | 所有交互元素可通过 Tab/Enter/Escape/方向键操作 |
| 焦点可见性 | 检查焦点样式对比度 | 焦点指示器对比度 >= 2:1 |
| 屏幕阅读器 | NVDA/VoiceOver 测试 | 所有元素有正确语义标签，动态内容可播报 |
| 颜色对比度 | axe DevTools 或 Lighthouse | 所有文本满足 WCAG 2.1 AA 对比度要求 |
| 表单标签 | 检查 label 关联 | 所有输入有标签关联 |
| ARIA 属性 | axe DevTools 扫描 | 无 ARIA 错误 |
| 响应式触摸目标 | 移动端测试 | 所有点击目标 >= 44x44px |

---

## 11. 性能优化方案

**修订说明（V9 -> V10）：** V9 未涉及性能优化方案，V10 补充完整的性能优化策略。

### 11.1 路由懒加载

所有路由组件已使用 `() => import()` 语法实现懒加载，Vue Router 会自动进行代码分割，每个路由成为一个独立的 chunk。

```typescript
// 示例：路由懒加载产生的 chunk 文件
// dist/assets/DashboardView-[hash].js
// dist/assets/ProjectListView-[hash].js
// dist/assets/ChatView-[hash].js
// ...
```

### 11.2 组件异步加载

对于大型或低频使用的组件，使用 `defineAsyncComponent` 实现异步加载：

```typescript
// 示例：异步加载 Markdown 编辑器
import { defineAsyncComponent } from 'vue';

const MDEditor = defineAsyncComponent(() =>
  import('md-editor-v3').then(m => ({
    render: () => h(m.default, props),
  }))
);
```

### 11.3 虚拟列表

**适用场景：**

| 组件 | 数据量 | 优化方案 |
|------|--------|---------|
| MessageList | 可能数百至数千条 | vue-virtual-scroller RecycleScroller |
| CommitList | 可能数百条提交 | vue-virtual-scroller RecycleScroller |
| ProjectList | 通常 < 100 条 | 无需虚拟滚动 |
| TaskKanban | 每列通常 < 50 条 | 无需虚拟滚动 |

**虚拟滚动实现：**

```vue
<!-- CommitList.vue 虚拟滚动示例 -->
<template>
  <RecycleScroller
    class="commit-scroller"
    :items="commits"
    :item-size="60"
    key-field="sha"
    v-slot="{ item }"
  >
    <CommitItem :commit="item" />
  </RecycleScroller>
</template>

<script setup lang="ts">
import { RecycleScroller } from 'vue-virtual-scroller';
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css';
</script>
```

### 11.4 图片懒加载

```vue
<!-- 使用 Element Plus 的 el-image 实现懒加载 -->
<template>
  <el-image
    :src="image.url"
    lazy
    fit="cover"
    :alt="image.alt"
  />
</template>
```

### 11.5 ECharts 性能优化

```typescript
// QAScoreChart.vue
// 大数据量时启用 ECharts 的增量渲染
const chartOption = {
  dataset: { source: data },
  series: [{
    type: 'radar',
    // 开启动画但限制帧率
    animationDuration: 500,
    animationEasing: 'cubicOut',
  }],
  // 禁用不必要的交互
  tooltip: { trigger: 'item' },
};
```

### 11.6 Vite 构建优化

```typescript
// vite.config.ts
export default defineConfig({
  // ... 其他配置
  build: {
    outDir: 'dist',
    sourcemap: true,
    // 手动配置 code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          elementPlus: ['element-plus'],
          echarts: ['echarts'],
        },
      },
    },
    // Gzip 压缩大小报告
    reportCompressedSize: true,
    chunkSizeWarningLimit: 500,
  },
});
```

### 11.7 HTTP 请求优化

1. **防抖搜索**：项目列表搜索框使用 300ms 防抖，减少不必要的 API 请求
2. **请求缓存**：项目列表、任务列表等数据设置短时间缓存（如 30 秒），重复请求直接返回缓存
3. **并发控制**：使用 Axios 请求取消机制，避免用户快速切换页面时产生过时请求
4. **分页加载**：长列表使用分页而非一次性加载全部数据

---

## 12. 测试策略

**修订说明（V9 -> V10）：** V9 完全缺失测试策略，V10 补充完整的单元测试和 E2E 测试方案。

### 12.1 单元测试（Vitest）

**测试范围：**

| 测试对象 | 覆盖内容 | 目标覆盖率 |
|---------|---------|-----------|
| composables | useWebSocket 连接/重连/断开逻辑 | 80% |
| stores | Pinia Store 的 actions 和 getters | 80% |
| utils | 工具函数（format.ts, errors.ts） | 90% |
| components | 复杂组件的渲染和交互逻辑 | 60% |

**Vitest 配置：**

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['tests/unit/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      reportsDirectory: './coverage',
      thresholds: {
        lines: 60,
        functions: 60,
        branches: 50,
      },
    },
  },
});
```

**单元测试示例：**

```typescript
// tests/unit/stores/userStore.test.ts
import { describe, it, expect, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useUserStore } from '@/stores/userStore';
import * as api from '@/api';

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it('login 应该存储 token 和用户信息', async () => {
    vi.spyOn(api, 'default', 'post').mockResolvedValue({
      data: {
        access_token: 'test-access',
        refresh_token: 'test-refresh',
        expires_in: 3600,
        user: { id: '1', username: 'test', email: 'test@example.com' },
      },
    });

    const store = useUserStore();
    await store.login('test', 'password');

    expect(store.accessToken).toBe('test-access');
    expect(store.user?.username).toBe('test');
    expect(localStorage.getItem('devflow_refresh_token')).toBe('test-refresh');
  });

  it('logout 应该清除所有状态和 localStorage', () => {
    const store = useUserStore();
    store.accessToken = 'token';
    localStorage.setItem('devflow_refresh_token', 'refresh');

    store.logout();

    expect(store.accessToken).toBeNull();
    expect(store.user).toBeNull();
    expect(localStorage.getItem('devflow_refresh_token')).toBeNull();
  });

  it('restoreSession 应该从 localStorage 恢复会话', async () => {
    localStorage.setItem('devflow_refresh_token', 'valid-refresh');
    vi.spyOn(api, 'default', 'post').mockResolvedValue({
      data: {
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        expires_in: 3600,
      },
    });

    const store = useUserStore();
    const result = await store.restoreSession();

    expect(result).toBe(true);
    expect(store.accessToken).toBe('new-access');
  });
});
```

```typescript
// tests/unit/composables/useWebSocket.test.ts
import { describe, it, expect, vi } from 'vitest';

describe('useWebSocket', () => {
  it('应该正确连接并发送加入消息', async () => {
    // 模拟 WebSocket
    const mockWs = {
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
    } as any as WebSocket;
    vi.stubGlobal('WebSocket', vi.fn(() => mockWs));

    const { connect } = useWebSocket();
    connect('group-1');

    // 触发 onopen
    mockWs.onopen();

    expect(mockWs.send).toHaveBeenCalledWith(JSON.stringify({
      type: 'chat.join',
      payload: { group_id: 'group-1' },
    }));
  });

  it('应该在非正常关闭时尝试重连', async () => {
    // 测试重连逻辑
  });
});
```

### 12.2 E2E 测试（Cypress）

**测试范围：**

| 测试场景 | 验证内容 | 优先级 |
|---------|---------|--------|
| 用户登录流程 | 登录成功/失败、token 存储、跳转 | P0 |
| 项目创建流程 | 表单验证、项目创建、列表更新 | P0 |
| 讨论群聊天 | 发送消息、接收消息、流式输出显示 | P0 |
| 任务看板拖拽 | 拖拽任务、状态更新、API 调用 | P1 |
| 路由守卫 | 未登录重定向、token 过期处理 | P1 |
| 响应式布局 | 移动端侧边栏抽屉、聊天布局切换 | P2 |

**Cypress 配置：**

```typescript
// cypress.config.ts
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5173',
    supportFile: 'tests/e2e/support/index.ts',
    specPattern: 'tests/e2e/spec/**/*.cy.ts',
    video: false,
    screenshotOnRunFailure: true,
  },
  component: {
    specPattern: 'tests/unit/components/**/*.cy.tsx',
  },
});
```

**E2E 测试示例：**

```typescript
// tests/e2e/spec/login.cy.ts
describe('用户登录流程', () => {
  it('应该能够成功登录并跳转到仪表板', () => {
    cy.visit('/login');
    cy.get('#username').type('testuser');
    cy.get('#password').type('testpassword');
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/dashboard');
  });

  it('登录失败应该显示错误提示', () => {
    cy.intercept('POST', '/api/auth/login', {
      statusCode: 401,
      body: { message: '用户名或密码错误' },
    }).as('login');

    cy.visit('/login');
    cy.get('#username').type('wrong');
    cy.get('#password').type('wrong');
    cy.get('button[type="submit"]').click();

    cy.get('.el-message--error').should('contain', '用户名或密码错误');
  });
});

// tests/e2e/spec/chat.cy.ts
describe('讨论群聊天', () => {
  it('应该能够发送消息并接收回复', () => {
    cy.visit('/projects/1/chat');

    // 发送消息
    cy.get('[aria-label="消息输入"]').type('你好');
    cy.get('[aria-label="发送消息"]').click();

    // 验证消息出现在列表中
    cy.get('[role="log"]').should('contain', '你好');
  });
});
```

### 12.3 CI/CD 集成

```yaml
# .github/workflows/test.yml 示例
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run test:unit -- --coverage
      - run: npm run build
      # E2E 测试（可选，需要启动开发服务器）
      # - run: npm run test:e2e
```

---

## 13. 构建与部署

### 13.1 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';

export default defineConfig({
  plugins: [
    vue(),
    Components({
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
          vue: ['vue', 'vue-router', 'pinia'],
          elementPlus: ['element-plus'],
          echarts: ['echarts'],
        },
      },
    },
  },
});
```

**修订说明（V9 -> V10）：** 移除 Nginx 中 SSE 长连接配置（`/api/stream` location），因 SSE 已统一为 WebSocket。

### 13.2 Docker 部署

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

### 13.3 Nginx 配置

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
    }

    location /ws {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
    }
}
```

**修订说明（V9 -> V10）：** 移除了 `/api/stream` location 块（SSE 专用），WebSocket 代理配置统一在 `/ws` location 中。

---

## 14. V9 -> V10 修订记录

| 编号 | 严重程度 | 后荣检验意见 | 修订内容 |
|------|----------|-------------|---------|
| 1 | 致命 | 文档严重不完整：在 3.2.2 章节处突然截断，后续章节全部缺失 | V9 实际包含了完整内容但后荣认为截断。V10 重新组织章节结构，确保所有章节完整、连贯，并补充了 V9 中缺失的性能优化和测试策略章节 |
| 2 | 严重 | 实时通信方案冗余且矛盾：同时引入 WebSocket 和 SSE | 统一使用 WebSocket 处理所有实时通信，移除 SSE/EventSource 相关设计。新增 `agent_stream_start`/`agent_stream_chunk`/`agent_stream_done` 消息类型。移除 `useSSE.ts` composable。移除 Nginx SSE 配置 |
| 3 | 中等 | Token 安全存储方案缺失 | 明确定义 access token 仅存于 Pinia 内存、refresh token 存于 localStorage 的方案。新增 `restoreSession()` 方法用于页面刷新后恢复会话。补充 Token 安全存储方案表格和安全设计要点 |
| 4 | 中等 | 无障碍实现细节缺失 | 第 10 章大幅扩充：补充键盘导航实现方案（焦点样式代码、快捷键、焦点管理）、ARIA 属性使用规范表格、色彩对比度验证数据、表单无障碍实现代码、屏幕阅读器支持方案、无障碍验证清单 |
| 5 | 中等 | 移动端响应式策略缺失 | 新增第 9.3 节响应式设计：定义 5 个断点（sm/md/lg/xl），提供 SCSS 混入和工具类，补充各断点的适配策略说明，包含侧边栏抽屉模式、聊天布局切换、看板列数调整等 |
| 6 | 中等 | API 层设计过于简单 | 第 5 章大幅扩充：补充完整响应拦截器（401/422/5xx/超时/网络错误统一处理）、APIError 自定义错误类、请求取消机制（CancelToken 管理）、统一错误处理工具函数（formatAPIError、isAPIError） |
| 7 | 中等 | 性能优化方案缺失 | 新增第 11 章性能优化方案：路由懒加载（已实现）、组件异步加载、虚拟列表（MessageList/CommitList）、图片懒加载、ECharts 性能优化、Vite 构建优化（manualChunks）、HTTP 请求优化（防抖/缓存/并发控制） |
| 8 | 中等 | 测试策略缺失 | 新增第 12 章测试策略：Vitest 单元测试配置和示例（stores、composables 测试）、Cypress E2E 测试配置和示例（登录、聊天流程）、CI/CD 集成示例、测试范围和目标覆盖率 |
