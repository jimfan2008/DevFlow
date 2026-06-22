# DevFlow 项目管理平台 - 前端设计文档

**版本**: V7  
**日期**: 2026-06-16  
**作者**: HouWang (后旺)  
**状态**: 修订版V7（等待后荣检验）

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
| HTTP 客户端 | Axios | 1.x | 拦截器、超时控制、取消请求 |
| WebSocket | 原生 WebSocket + ReconnectingWebSocket | - | 实时消息推送 |
| 路由 | Vue Router | 4.x | Vue 3 官方路由 |
| 国际化 | vue-i18n | 9.x | 多语言支持 |
| 代码规范 | ESLint + Prettier | - | 统一代码风格 |
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
│   │   └── constants.ts        # 常量定义
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

### 2.1 登录页 (LoginView)

**路由**: `/login`

| 元素 | 说明 |
|------|------|
| 用户名输入 | 必填，最大 50 字符 |
| 密码输入 | 必填，显示/隐藏切换 |
| 记住我 | 可选 checkbox |
| 登录按钮 | 主按钮，加载状态显示 |

### 2.2 首页/仪表板 (DashboardView)

**路由**: `/dashboard`

| 区域 | 内容 |
|------|------|
| 顶部统计卡片 | 项目总数、进行中项目、待处理通知、Agent 在线数 |
| 项目进度图表 | ECharts 饼图/柱状图展示各项目进度 |
| 最近项目列表 | 最近 5 个项目的精简卡片 |
| Agent 负载状态 | 9 个命名 Agent 的状态列表（在线/离线/忙碌） |
| 通知摘要 | 最近 3 条未读通知 |

### 2.3 项目列表页 (ProjectListView)

**路由**: `/projects`

| 功能 | 说明 |
|------|------|
| 创建项目按钮 | 右上角主按钮，弹出创建项目表单 |
| 项目卡片网格 | 每行 3 张卡片（桌面端），每张显示项目名称、状态、进度、创建时间 |
| 筛选/搜索 | 按状态筛选（全部/进行中/已完成/已取消）、按名称搜索 |
| 排序 | 按创建时间倒序（默认） |

**创建项目表单字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 项目名称 | 文本输入 | 是 | 最大 200 字符 |
| 项目描述 | 多行文本 | 否 | 支持 Markdown |
| 初始需求 | 富文本编辑器 | 否 | 支持附件上传 |

### 2.4 项目详情页 (ProjectDetailView)

**路由**: `/projects/:id`

| 区域 | 内容 |
|------|------|
| 项目信息卡片 | 项目名称、状态、进度条、创建时间、负责人 |
| 核心目标 | 海梅与用户确认的核心目标文本 |
| 任务看板 | 按状态分列的看板视图（待处理/进行中/已完成/失败/已取消） |
| 项目讨论群入口 | 进入聊天页面的按钮 |
| Agent 分配情况 | 9 个 Agent 在本项目中的状态和任务数 |
| 代码仓库入口 | 跳转到代码仓库页面的链接 |
| QA 检验统计 | 总检验数、通过率、平均分 |

### 2.5 讨论群聊天页 (ChatView)

**路由**: `/projects/:id/chat`

这是 DevFlow 的核心交互页面，支持讨论模式和会议模式两种工作模式。

**页面布局**：

```
┌──────────────────────────────────────────────────────────────┐
│  [项目讨论群]  [讨论模式 ▼]  [成员列表]  [设置]              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────┐           │
│  │ 后兴 (需求分析师)  14:30                      │           │
│  │ ┌──────────────────────────────────────────┐ │           │
│  │ │ 根据用户需求分析，SRS 已完成初稿...       │ │           │
│  │ └──────────────────────────────────────────┘ │           │
│  │  ↑ Agent 消息（蓝色气泡，左对齐）              │           │
│  ├──────────────────────────────────────────────┤           │
│  │                           老板  14:35         │           │
│  │                    ┌──────────────────────┐   │           │
│  │                    │ 需求第 3 项需要调整... │   │           │
│  │                    └──────────────────────┘   │           │
│  │  ↑ 用户消息（绿色气泡，右对齐）                  │           │
│  ├──────────────────────────────────────────────┤           │
│  │ 系统通知  14:36                               │           │
│  │ ─── 海梅已分配架构设计任务给后旺 ───           │           │
│  │  ↑ 系统消息（灰色，居中显示）                    │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 输入消息...                    [@] [文件] [发送 ▶]    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**消息类型与样式**：

| 消息类型 | 样式 | 来源 |
|----------|------|------|
| 用户消息 (user) | 绿色气泡，右对齐 | 人类用户 |
| Agent 消息 (agent) | 蓝色气泡，左对齐 | Agent 发送 |
| 系统通知 (system) | 灰色，居中，分隔线样式 | 系统自动生成 |

**功能特性**：

| 功能 | 说明 |
|------|------|
| @mention | 输入 `@` 弹出 Agent/用户选择列表，@Agent 定向沟通 |
| 实时推送 | WebSocket 接收新消息，实时显示 |
| 流式输出 | Agent 消息支持 SSE 流式输出，逐字显示 |
| 消息时间轴 | 按时间正序排列，支持滚动加载历史消息 |
| 附件上传 | 支持图片、文档附件 |
| 会议模式切换 | 下拉菜单切换讨论/会议模式 |

**会议模式额外功能**：

| 功能 | 说明 |
|------|------|
| 议程管理 | 主持人可添加/修改/删除议程项 |
| 决议记录 | 结构化记录会议决议 |
| 待办生成 | 会议待办自动关联任务 |
| 风险记录 | 识别和记录项目风险 |
| 会议纪要 | 自动生成结构化会议纪要 |

### 2.6 任务看板页 (TaskView)

**路由**: `/projects/:id/tasks`

| 列 | 对应任务状态 |
|----|------------|
| 待处理 | pending |
| 进行中 | in_progress |
| 已完成 | completed |
| 失败 | failed |
| 已取消 | cancelled |

**任务卡片字段**：

| 字段 | 说明 |
|------|------|
| 任务名称 | 点击展开详情 |
| 任务类型 | 标签显示（如"架构设计"、"代码编写"） |
| 分配者 | Agent 徽章或用户名 |
| 优先级 | 数字显示 |
| 步骤编号 | step_number |
| 预估/实际工时 | 小数显示 |

### 2.7 QA 检验页 (QAView)

**路由**: `/projects/:id/qa`

| 区域 | 内容 |
|------|------|
| 检验统计 | 总检验数、通过数、失败数、通过率、平均分 |
| 评分图表 | 各维度得分雷达图（完整性、一致性、可验证性、无歧义性） |
| 检验记录列表 | 按时间倒序，显示任务名称、检验结果、评分、问题详情 |
| 详情展开 | 点击检验记录展开各维度详细评分和问题描述 |

### 2.8 代码仓库页 (RepoView)

**路由**: `/projects/:id/repo`

| 功能 | 说明 |
|------|------|
| 仓库信息 | 仓库名称、URL、默认分支、公开/私有状态 |
| 提交列表 | 按时间倒序，显示 SHA 前 7 位、提交信息、作者、时间 |
| 分支列表 | 分支名称、最新提交 SHA、保护状态 |
| PR 列表 | PR 编号、标题、状态、源/目标分支、作者 |
| Gitea 链接 | 外部链接到 Gitea Web 界面 |

### 2.9 Agent 管理页 (Agent 状态查看)

**路由**: `/agents`

| 区域 | 内容 |
|------|------|
| Agent 列表 | 9 个命名 Agent 卡片，显示名称、中文名、角色、状态 |
| 负载统计 | 每个 Agent 的任务分配情况（总任务、进行中、待处理） |
| 蜂群信息 | 当前活跃的 Agent 蜂群列表 |

### 2.10 系统设置页 (SettingsView)

**路由**: `/settings`

| 功能 | 说明 |
|------|------|
| 用户信息 | 用户名、邮箱、角色 |
| 语言切换 | 中/英下拉选择 |
| 通知偏好 | 各类通知的开启/关闭 |
| 主题设置 | 浅色/深色主题切换 |

---

## 3. 组件设计

### 3.1 项目卡片 (ProjectCard)

| 属性 | 类型 | 说明 |
|------|------|------|
| project | Project | 项目对象 |
| show-progress | boolean | 是否显示进度条 |

| 事件 | 说明 |
|------|------|
| click | 点击进入项目详情 |

### 3.2 任务卡片 (TaskCard)

| 属性 | 类型 | 说明 |
|------|------|------|
| task | Task | 任务对象 |
| draggable | boolean | 是否可拖拽（看板模式下为 true） |

| 事件 | 说明 |
|------|------|
| drag-start | 拖拽开始 |
| drag-end | 拖拽结束 |

### 3.3 消息气泡 (MessageBubble)

| 属性 | 类型 | 说明 |
|------|------|------|
| message | Message | 消息对象（含 content, type, timestamp, sender） |
| streaming | boolean | 是否正在流式输出 |

### 3.4 Agent 状态徽章 (AgentBadge)

| 属性 | 类型 | 说明 |
|------|------|------|
| agent | Agent | Agent 对象 |
| size | 'small' \| 'medium' \| 'large' | 徽章大小 |

| 状态颜色 | 对应值 | 颜色 |
|----------|--------|------|
| 在线 | online | 绿色 |
| 离线 | offline | 灰色 |
| 忙碌 | busy | 橙色 |

### 3.5 聊天窗口 (ChatWindow)

| 属性 | 类型 | 说明 |
|------|------|------|
| group-id | number | 项目讨论群 ID |
| mode | 'discussion' \| 'meeting' | 工作模式 |

| 方法 | 说明 |
|------|------|
| sendMessage | 发送消息 |
| switchMode | 切换讨论/会议模式 |

---

## 4. 路由设计

### 4.1 路由表

| 路径 | 组件 | 名称 | 守卫 |
|------|------|------|------|
| /login | LoginView | login | 未登录时重定向到此 |
| /dashboard | DashboardView | dashboard | 需登录 |
| /projects | ProjectListView | project-list | 需登录 |
| /projects/create | 嵌入在 ProjectListView 中 | - | 需登录 |
| /projects/:id | ProjectDetailView | project-detail | 需登录 |
| /projects/:id/chat | ChatView | project-chat | 需登录 |
| /projects/:id/tasks | TaskView | project-tasks | 需登录 |
| /projects/:id/qa | QAView | project-qa | 需登录 |
| /projects/:id/repo | RepoView | project-repo | 需登录 |
| /agents | Agent 状态查看（嵌入默认布局） | agents | 需登录 |
| /settings | SettingsView | settings | 需登录 |
| /404 | NotFoundView | not-found | - |
| /:pathMatch(.*)* | NotFoundView | not-found | - |

### 4.2 路由守卫

```typescript
// 登录守卫
router.beforeEach((to, from, next) => {
  const isAuthenticated = useUserStore().isAuthenticated;
  
  if (to.name !== 'login' && !isAuthenticated) {
    next({ name: 'login' });
  } else if (to.name === 'login' && isAuthenticated) {
    next({ name: 'dashboard' });
  } else {
    next();
  }
});
```

---

## 5. 状态管理

### 5.1 Pinia Store 设计

#### userStore

```typescript
interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  token: string | null;
}

// 方法
defineActions({
  login(username: string, password: string): Promise<void>,
  logout(): Promise<void>,
  fetchUser(): Promise<void>
});
```

#### projectStore

```typescript
interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
}

// 方法
defineActions({
  fetchProjects(): Promise<void>,
  fetchProject(id: number): Promise<void>,
  createProject(data: CreateProjectDTO): Promise<Project>,
  updateProject(id: number, data: UpdateProjectDTO): Promise<void>
});
```

#### taskStore

```typescript
interface TaskState {
  tasks: Task[];
  filteredTasks: Task[];
  loading: boolean;
}

// 方法
defineActions({
  fetchTasks(projectId: number): Promise<void>,
  filterByStatus(status: string): void,
  updateTaskStatus(taskId: number, status: string): Promise<void>
});
```

#### chatStore

```typescript
interface ChatState {
  messages: Message[];
  currentGroup: Group | null;
  mode: 'discussion' | 'meeting';
  wsConnected: boolean;
}

// 方法
defineActions({
  connectWebSocket(groupId: number): void,
  disconnectWebSocket(): void,
  sendMessage(content: string, mentionAgentId?: number): Promise<void>,
  fetchMessages(groupId: number, offset: number = 0): Promise<void>,
  switchMode(mode: 'discussion' | 'meeting'): void
});
```

#### notificationStore

```typescript
interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  loading: boolean;
}

// 方法
defineActions({
  fetchNotifications(): Promise<void>,
  markAsRead(id: number): Promise<void>,
  markAllAsRead(): Promise<void>
});
```

#### settingStore

```typescript
interface SettingState {
  language: 'zh-CN' | 'en-US';
  theme: 'light' | 'dark';
  notificationPreferences: NotificationPreference;
}

// 方法
defineActions({
  setLanguage(lang: 'zh-CN' | 'en-US'): void,
  setTheme(theme: 'light' | 'dark'): void,
  updateNotificationPreferences(prefs: Partial<NotificationPreference>): void
});
```

---

## 6. API 对接

### 6.1 Axios 实例配置

```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

// 请求拦截器：添加认证 token
api.interceptors.request.use(config => {
  const token = useUserStore().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      useUserStore().logout();
      router.push({ name: 'login' });
    }
    return Promise.reject(error);
  }
);
```

### 6.2 API 模块示例

```typescript
// api/project.ts
export const projectApi = {
  list: () => api.get('/projects'),
  detail: (id: number) => api.get(`/projects/${id}`),
  create: (data: CreateProjectDTO) => api.post('/projects', data),
  update: (id: number, data: UpdateProjectDTO) => api.put(`/projects/${id}`, data)
};
```

---

## 7. WebSocket 实时通信

### 7.1 连接管理

```typescript
// composables/useWebSocket.ts
export function useWebSocket() {
  const ws = ref<WebSocket | null>(null);
  const connected = ref(false);
  const reconnectAttempts = ref(0);
  const maxReconnectAttempts = 5;

  function connect(groupId: number) {
    const url = `${import.meta.env.VITE_WS_URL}/ws/groups/${groupId}`;
    ws.value = new WebSocket(url);

    ws.value.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
    };

    ws.value.onmessage = (event) => {
      const message = JSON.parse(event.data);
      // 根据事件类型分发处理
      handleWebSocketMessage(message);
    };

    ws.value.onclose = () => {
      connected.value = false;
      scheduleReconnect(groupId);
    };

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error);
      ws.value?.close();
    };
  }

  function scheduleReconnect(groupId: number) {
    if (reconnectAttempts.value < maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);
      setTimeout(() => {
        reconnectAttempts.value++;
        connect(groupId);
      }, delay);
    }
  }

  function disconnect() {
    ws.value?.close();
    connected.value = false;
  }

  return { connect, disconnect, connected };
}
```

### 7.2 事件类型

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| message.new | 服务端→客户端 | 新消息推送 |
| message.update | 服务端→客户端 | 消息更新（如流式输出追加） |
| message.send | 客户端→服务端 | 发送消息 |
| mode.change | 客户端→服务端 | 切换讨论/会议模式 |
| user.join | 服务端→客户端 | 用户/Agent 加入群组 |
| user.leave | 服务端→客户端 | 用户/Agent 离开群组 |
| connection.open | 双向 | 连接建立确认 |
| connection.close | 双向 | 连接关闭 |
| heartbeat.ping | 客户端→服务端 | 心跳检测 |
| heartbeat.pong | 服务端→客户端 | 心跳响应 |

---

## 8. 响应式布局

### 8.1 断点设计

| 断点 | 范围 | 设备 | 布局 |
|------|------|------|------|
| xs | < 640px | 手机 | 单列，隐藏侧边栏 |
| sm | 640px - 768px | 平板竖屏 | 单列，汉堡菜单 |
| md | 768px - 1024px | 平板横屏 | 双列，可收缩侧边栏 |
| lg | 1024px - 1280px | 笔记本 | 三列，固定侧边栏 |
| xl | > 1280px | 桌面 | 三列及以上，完整布局 |

### 8.2 移动端适配

- 导航栏：汉堡菜单，侧滑面板
- 项目卡片：每行 1 张
- 任务看板：水平滚动或折叠为列表视图
- 聊天界面：全屏模式，底部固定输入框
- 图表：简化为柱状图或数据列表

---

## 9. 国际化与多语言

### 9.1 i18n 配置

```typescript
// i18n/index.ts
export const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  }
});
```

### 9.2 默认语言

- 默认语言：中文 (zh-CN)
- 支持切换：中/英
- 语言偏好保存到 localStorage 和后端

### 9.3 语言包结构

```json
{
  "common": {
    "save": "保存",
    "cancel": "取消",
    "delete": "删除",
    "search": "搜索"
  },
  "project": {
    "create": "创建项目",
    "name": "项目名称",
    "description": "项目描述",
    "status": {
      "created": "已创建",
      "in_progress": "进行中",
      "completed": "已完成",
      "cancelled": "已取消"
    }
  },
  "chat": {
    "input_placeholder": "输入消息...",
    "send": "发送",
    "mention": "@Agent 定向沟通"
  }
}
```

---

## 10. 无障碍访问

### 10.1 ARIA 标签

- 所有图标按钮添加 `aria-label`
- 聊天消息添加 `role="log"` 和 `aria-live="polite"`
- 表单字段关联 `aria-describedby` 说明文字
- 通知区域添加 `role="alert"`

### 10.2 键盘导航

- Tab 键导航所有可交互元素
- Enter 键提交表单
- Esc 键关闭弹窗
- 聊天界面：Enter 发送，Shift+Enter 换行

### 10.3 色彩对比度

- 文字与背景对比度 ≥ 4.5:1（WCAG AA 级）
- Agent 状态颜色：绿色(#67C23A)、灰色(#909399)、橙色(#E6A23C) 均满足对比度要求
- 不单独依赖颜色传递信息（如 Agent 状态同时用颜色 + 文字）

### 10.4 屏幕阅读器

- 图片添加 `alt` 属性
- 动态内容更新时通过 `aria-live` 通知
- 任务看板使用 `role="list"` 和 `role="listitem"`
- 聊天消息使用 `role="listbox"`

---

## 11. 性能优化

### 11.1 懒加载

- 路由级懒加载：所有视图组件使用 `defineAsyncComponent` 或动态导入
- 图片懒加载：使用 `v-lazy` 或 IntersectionObserver
- 图表按需加载：ECharts 按需引入模块

### 11.2 代码分割

- Vite 自动按路由分割代码
- Element Plus 组件按需引入，减小打包体积
- 大型依赖（如 ECharts）单独拆分 chunk

### 11.3 缓存策略

- 静态资源：长期缓存（1 年），文件名含 hash
- API 数据：项目列表缓存 5 分钟，聊天消息不缓存
- 语言包：首次加载后缓存到 localStorage

### 11.4 消息列表虚拟滚动

- 聊天消息列表使用虚拟滚动（vue-virtual-scroller）
- 只渲染可视区域的消息，减少 DOM 节点数
- 历史消息通过滚动向上时动态加载

---

## 12. 构建与部署

### 12.1 Vite 配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'echarts': ['echarts'],
          'vendor': ['vue', 'vue-router', 'pinia']
        }
      }
    }
  }
});
```

### 12.2 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| VITE_API_BASE_URL | API 基础 URL | /api/v1 |
| VITE_WS_URL | WebSocket URL | ws://localhost:8000 |
| VITE_GITEA_URL | Gitea Web URL | http://localhost:3000 |

### 12.3 Docker 部署

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
CMD ["nginx", "-g", "daemon off;"]
```

### 12.4 CI/CD 集成

- 代码推送到 main 分支触发自动构建
- 运行 lint + test + build
- 构建产物推送至 Docker Registry
- 部署到测试/生产环境

---

**文档结束**
