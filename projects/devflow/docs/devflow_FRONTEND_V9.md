# DevFlow 项目管理平台 - 前端设计文档

**版本**: V9  
**日期**: 2026-06-16  
**作者**: HouWang (后旺)  
**状态**: 修订版V9（等待后荣检验）

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
| WebSocket | 原生 WebSocket（自定义重连逻辑） | - | 实时消息推送 |
| 路由 | Vue Router | 4.x | Vue 3 官方路由 |
| 国际化 | vue-i18n | 9.x | 多语言支持 |
| 代码规范 | ESLint + Prettier | - | 统一代码风格 |
| SSE 流式输出 | 原生 EventSource | - | Agent 流式输出 |
| 拖拽库 | vue-draggable-plus | 2.x | Vue3 拖拽库，支持看板拖拽排序 |
| CSS 预处理 | SCSS | - | 变量、嵌套、混入 |
| 图标库 | @element-plus/icons-vue | - | 与 Element Plus 风格统一 |
| 富文本编辑器 | @tiptap/vue-3 | - | 需求描述、文档编辑 |
| Markdown 预览 | md-editor-v3 | - | SRS 等文档预览 |
| 图表 | ECharts | 5.x | 项目进度、Agent 负载统计 |

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
│   │       ├── variables.scss  # 主题变量
│   │       └── mixins.scss     # 样式混入
│   ├── components/             # 通用组件
│   │   ├── common/             # 基础组件
│   │   │   ├── AppHeader.vue   # 顶部导航
│   │   │   ├── AppSidebar.vue  # 侧边栏
│   │   │   ├── AppFooter.vue   # 底部信息
│   │   │   ├── AgentBadge.vue  # Agent 状态徽章
│   │   │   └── StatusDot.vue   # 状态指示灯
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
│   │   ├── useWebSocket.ts     # WebSocket 连接
│   │   ├── useSSE.ts           # SSE 流式输出
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
├── index.html
├── vite.config.ts              # Vite 配置
├── tsconfig.json               # TypeScript 配置
├── .eslintrc.cjs               # ESLint 配置
├── .prettierrc                 # Prettier 配置
└── package.json
```

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
- 文档区域：SRS、架构设计文档等，使用 md-editor-v3 预览
- Agent 分配情况列表

#### 2.2.5 讨论群聊天 (/projects/:id/chat)

- 左侧：讨论群列表（当前项目的多个讨论群）
- 中间：消息列表，区分用户消息和 Agent 消息
- 底部：消息输入框，支持富文本
- Agent 消息支持 SSE 流式输出显示
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
- 提交记录列表（CommitList 组件），支持分页
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

### 3.2 聊天相关组件

#### 3.2.1 ChatWindow（聊天窗口）

```typescript
interface ChatWindowProps {
  groupId: string;
  projectId: string;
}
```

- 集成 MessageList、MessageInput 子组件
- 连接 WebSocket 获取实时消息
- 连接 SSE 获取 Agent 流式输出
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

- 虚拟滚动渲染（messages 量大时性能优化）
- 按时间分组显示（今天、昨天、更早）
- 流式消息实时追加渲染

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
    clearStreamingContent(messageId: string) {
      this.streamingContent.delete(messageId);
    },
    connectWebSocket(groupId: string) {
      useWebSocket().connect(groupId);
    },
    disconnectWebSocket() {
      useWebSocket().disconnect();
    },
    startSSEStream(messageId: string, url: string) {
      useSSE().startStream(messageId, url, {
        onChunk: (chunk) => {
          this.setStreamingContent(messageId, chunk);
        },
        onDone: (fullContent) => {
          const msg = this.messages.find(m => m.id === messageId);
          if (msg) msg.content = fullContent;
          this.clearStreamingContent(messageId);
        },
      });
    },
    stopSSEStream(messageId: string) {
      useSSE().stopStream(messageId);
    },
  },
});
```

**Store 与 composable 的调用关系：**

- `connectWebSocket` / `disconnectWebSocket`：chatStore 委托 useWebSocket composable 处理底层 WebSocket 连接生命周期
- `startSSEStream` / `stopSSEStream`：chatStore 委托 useSSE composable 按 messageId 独立管理每个 SSE 连接
- composable 负责连接管理，Store 负责状态更新和消息协调

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

// 响应拦截器：token 刷新（详见 4.1 节）
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
| GET | /groups/:id/messages/:id/stream | SSE 流式输出 |

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

## 6. WebSocket 与 SSE 通信设计

### 6.1 通信职责划分

**WebSocket 负责的事件（双向实时通信）：**

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| message.new | Server -> Client | 新消息推送（消息已完成） |
| message.deleted | Server -> Client | 消息删除通知 |
| agent.status | Server -> Client | Agent 状态变更 |
| task.updated | Server -> Client | 任务状态变更 |
| project.step.changed | Server -> Client | 项目步骤推进 |
| notification | Server -> Client | 系统通知推送 |
| chat.join | Client -> Server | 加入讨论群 |
| chat.leave | Client -> Server | 离开讨论群 |
| message.send | Client -> Server | 发送消息 |

**SSE 负责的事件（单向流式输出）：**

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| stream.chunk | Server -> Client | Agent 回复内容增量追加 |
| stream.done | Server -> Client | Agent 回复完成 |
| stream.error | Server -> Client | 流式输出错误 |

**职责边界说明：**

- WebSocket 推送的是**已完成的消息**（message.new），即 Agent 回复完成后整条消息的推送通知
- SSE 负责的是**流式输出的过程展示**，即 Agent 正在生成回复时的逐字/逐块显示
- 两者不重复：SSE 流结束后，客户端已拥有完整消息内容；WebSocket 的 message.new 仅在消息通过其他途径变更（如删除、编辑）时推送
- 前端流程：用户发送消息 -> 后端创建 SSE 端点 -> 前端调用 useSSE().startStream() -> SSE 逐块更新 UI -> SSE 结束 -> 消息完整显示
- WebSocket 不承担流式输出功能，仅用于状态变更和新消息通知

### 6.2 WebSocket 连接管理（useWebSocket composable）

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
  let eventHandlers: Map<string, Function[]> = new Map();

  const getWsUrl = () => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || location.host;
    return `${protocol}//${host}/ws`;
  };

  const connect = (groupId?: string) => {
    if (ws.value) return;
    ws.value = new WebSocket(getWsUrl());

    ws.value.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
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
    }
  };

  const attemptReconnect = (groupId?: string) => {
    const maxAttempts = 5;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);
    reconnectAttempts.value++;
    if (reconnectAttempts.value <= maxAttempts) {
      setTimeout(() => connect(groupId), delay);
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
    connect,
    disconnect,
    on,
    off,
  };
}
```

**重连机制：**

- 最大重连次数：5 次
- 指数退避：1s -> 2s -> 4s -> 8s -> 16s（上限 30s）
- 重连成功后重置计数器
- 超过最大次数后停止重连，通知用户

### 6.3 SSE 流式输出（useSSE composable）

**修正说明（V8 -> V9）：**

V8 版本中 useSSE 使用单个 eventSource ref，多个 SSE 连接会互相覆盖。V9 改为 `Map<string, EventSource>` 按 messageId 独立管理每个 SSE 连接。同时修正 onerror 处理逻辑，区分正常结束和连接异常。

```typescript
// src/composables/useSSE.ts
interface SSEOptions {
  onChunk: (content: string) => void;
  onDone: (fullContent: string) => void;
  onError?: (error: Error) => void;
}

interface SSEConnection {
  source: EventSource;
  accumulated: string;
  options: SSEOptions;
  isCompleted: boolean;
}

export function useSSE() {
  // 按 messageId 独立管理每个 SSE 连接
  const connections = new Map<string, SSEConnection>();

  const startStream = (messageId: string, url: string, options: SSEOptions) => {
    // 如果已有同 messageId 的连接，先关闭
    if (connections.has(messageId)) {
      stopStream(messageId);
    }

    const source = new EventSource(url);
    const conn: SSEConnection = {
      source,
      accumulated: '',
      options,
      isCompleted: false,
    };

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);

      // 收到流式结束标记，正常清理
      if (data.type === 'stream.done' || data.done === true) {
        conn.isCompleted = true;
        options.onDone(conn.accumulated);
        source.close();
        connections.delete(messageId);
        return;
      }

      // 收到流式内容增量
      if (data.type === 'stream.chunk' || data.content) {
        const chunk = data.content || data.text || '';
        conn.accumulated += chunk;
        options.onChunk(conn.accumulated);
      }
    };

    // onerror 处理：不主动 close，让浏览器自动重连
    // EventSource 的 onerror 在连接断开时触发，但浏览器会自动重连
    // 仅在实际错误事件（event.type === 'error'）或流已完成时才清理
    source.onerror = (event) => {
      // EventSource 连接断开时 event.type 为 'error'
      // 如果流已正常完成，直接清理
      if (conn.isCompleted) {
        source.close();
        connections.delete(messageId);
        return;
      }

      // EventSource.readyState: 0=CONNECTING, 1=OPEN, 2=CLOSED
      if (source.readyState === EventSource.CLOSED) {
        // 连接已彻底关闭且未完成，触发错误回调
        if (options.onError) {
          options.onError(new Error('SSE connection closed unexpectedly'));
        }
        source.close();
        connections.delete(messageId);
      }
      // readyState === CONNECTING 表示浏览器正在自动重连，不做处理
      // readyState === OPEN 表示连接正常，onerror 可能是瞬时波动
    };

    connections.set(messageId, conn);
  };

  const stopStream = (messageId: string) => {
    const conn = connections.get(messageId);
    if (conn) {
      conn.isCompleted = true;
      conn.source.close();
      connections.delete(messageId);
    }
  };

  const stopAllStreams = () => {
    connections.forEach((_, id) => stopStream(id));
  };

  return {
    connections,
    startStream,
    stopStream,
    stopAllStreams,
  };
}
```

**SSE onerror 处理策略说明：**

| 场景 | readyState | 处理方式 |
|------|-----------|----------|
| 正常结束（收到 stream.done） | OPEN | 主动 close() 并清理 |
| 连接断开，浏览器自动重连中 | CONNECTING | 不做处理，等待重连 |
| 连接彻底关闭 | CLOSED | 触发 onError 回调并清理 |
| 瞬时波动（连接仍 OPEN） | OPEN | 不做处理 |

**多 Agent 同时回复场景：**

讨论群中若多个 Agent 同时回复用户，每个回复拥有独立的 messageId，useSSE 通过 `Map<string, SSEConnection>` 独立管理：

```
用户发送消息 "请分析需求"
  -> Agent A 开始回复 (messageId: msg-001)
     useSSE.startStream('msg-001', '/api/groups/1/messages/msg-001/stream')
  -> Agent B 开始回复 (messageId: msg-002)
     useSSE.startStream('msg-002', '/api/groups/1/messages/msg-002/stream')
  -> connections Map 中有两个独立连接，互不干扰
  -> Agent A 回复完成 -> connections.delete('msg-001')
  -> Agent B 回复完成 -> connections.delete('msg-002')
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

### 9.3 响应式断点

```scss
$breakpoint-sm: 576px;
$breakpoint-md: 768px;
$breakpoint-lg: 992px;
$breakpoint-xl: 1200px;
```

---

## 10. 无障碍设计（WCAG 2.1 AA）

### 10.1 键盘导航

- 所有交互元素可通过 Tab 键访问
- 焦点样式清晰可见（2:1 对比度）
- 跳过导航链接（Skip to main content）

### 10.2 屏幕阅读器支持

- 所有图片包含 alt 文本
- 图标按钮包含 aria-label
- 动态内容更新使用 aria-live 区域
- 聊天消息更新使用 aria-live="polite"

### 10.3 色彩对比度

- 正文文本对比度 >= 4.5:1
- 大文本对比度 >= 3:1
- 不单独依赖颜色传达信息（状态标签同时使用颜色和文字）

### 10.4 表单无障碍

- 所有输入框关联 label
- 错误提示使用 aria-describedby
- 必填字段使用 aria-required

---

## 11. 构建与部署

### 11.1 Vite 配置

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
  },
});
```

### 11.2 Docker 部署

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

### 11.3 Nginx 配置

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
    }

    # SSE 长连接配置
    location /api/stream {
        proxy_pass http://backend:8080;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## 12. V8 -> V9 修订记录

| 编号 | 严重程度 | 后荣检验意见 | 修订内容 |
|------|----------|-------------|---------|
| 1 | 严重 | SSE 使用单个 eventSource ref，多 Agent 同时回复会覆盖 | 改为 `Map<string, SSEConnection>` 按 messageId 独立管理每个 SSE 连接 |
| 2 | 严重 | SSE onerror 处理过于激进，网络波动即终止 | 区分 readyState 状态：CONNECTING 时等待浏览器自动重连，仅 CLOSED 且未完成时才触发错误 |
| 3 | 中等 | WebSocket 与 SSE 职责边界不清，存在双重更新风险 | 明确划分：WebSocket 仅负责状态变更和新消息通知（已完成的消息），SSE 负责流式输出过程展示，两者不重复 |
| 4 | 轻微 | 缺少 token 刷新机制 | 新增 refresh token 机制：登录返回 refresh token，Axios 拦截器自动刷新，排队处理并发请求 |
| 5 | 轻微 | chatStore 中 connectWebSocket/disconnectWebSocket 为空注释 | 落地实现：Store 委托 useWebSocket composable 处理连接，明确 Store 与 composable 的调用关系 |
| 6 | 轻微 | 任务看板拖拽未指定拖拽库 | 明确使用 vue-draggable-plus (2.x) 实现看板拖拽，补充安装命令和使用示例 |