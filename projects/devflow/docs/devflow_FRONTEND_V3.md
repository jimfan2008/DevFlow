# DevFlow 项目管理平台 - 前端设计文档

**版本**: V3  
**日期**: 2026-06-12  
**作者**: HouWang (后旺)  
**状态**: 修订版

---

## 1. 前端技术栈

### 1.1 核心技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架，使用 Composition API |
| Element Plus | 2.x | UI 组件库 |
| Vue Router | 4.x | 路由管理 |
| Pinia | 2.x | 状态管理 |
| Vite | 5.x | 构建工具 |
| Axios | 1.x | HTTP 客户端 |
| WebSocket | native | 实时通信 |
| Vue I18n | 9.x | 国际化支持 |
| TypeScript | 5.x | 类型安全 |
| Vitest | 1.x | 单元测试 |
| ECharts | 5.x | 图表渲染（步骤进度图、任务统计、Agent状态图表） |

### 1.2 辅助工具

| 工具 | 用途 |
|------|------|
| ESLint | 代码规范检查 |
| Prettier | 代码格式化 |
| Vue DevTools | 开发调试工具 |
| Day.js | 时间处理 |
| Lodash-es | 工具函数库 |
| Monaco Editor | 代码编辑器（API文档查看） |
| Markdown-it | Markdown 渲染 |
| ECharts | 数据可视化图表 |

---

## 2. 项目目录结构

```
devflow-frontend/
├── public/                    # 静态资源
│   └── favicon.ico
├── src/
│   ├── assets/               # 资源文件
│   │   ├── images/
│   │   ├── styles/
│   │   └── fonts/
│   ├── components/           # 通用组件
│   │   ├── common/           # 基础组件
│   │   ├── layout/           # 布局组件
│   │   ├── chart/            # 图表组件
│   │   └── editor/           # 编辑器组件
│   ├── views/                # 页面视图
│   │   ├── auth/             # 认证页面
│   │   ├── dashboard/        # 仪表盘
│   │   ├── project/          # 项目管理
│   │   │   └── tabs/         # 项目详情标签页组件
│   │   ├── agent/            # Agent管理
│   │   ├── group/            # 群组管理
│   │   └── admin/            # 管理后台
│   ├── stores/               # Pinia 状态管理
│   │   ├── user.ts
│   │   ├── project.ts
│   │   ├── agent.ts
│   │   ├── group.ts
│   │   └── websocket.ts
│   ├── router/               # 路由配置
│   │   ├── index.ts
│   │   └── guards.ts
│   ├── api/                  # API 接口
│   │   ├── auth.ts
│   │   ├── project.ts
│   │   ├── agent.ts
│   │   ├── group.ts
│   │   └── swarm.ts
│   ├── utils/                # 工具函数
│   │   ├── request.ts        # Axios 封装
│   │   ├── websocket.ts      # WebSocket 封装
│   │   ├── format.ts         # 格式化函数
│   │   └── validate.ts       # 验证函数
│   ├── types/                # TypeScript 类型定义
│   │   ├── project.d.ts
│   │   ├── agent.d.ts
│   │   ├── group.d.ts
│   │   ├── api.d.ts
│   │   └── websocket.d.ts
│   ├── locales/              # 国际化语言包（ES模块导入）
│   │   ├── zh-CN.ts
│   │   └── en-US.ts
│   ├── App.vue
│   └── main.ts
├── tests/                    # 测试文件
│   ├── unit/
│   └── e2e/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

**语言包说明**: 语言包放在 src/locales/ 目录下作为 ES 模块导入，利用 Vite 的 tree-shaking 和按需加载能力。文件格式改为 .ts 以支持 TypeScript 类型安全。public/ 是纯静态资源目录，不适合放需要动态 import 的语言包。

---

## 3. 组件树设计

### 3.1 根组件 (App.vue)

```
App
├── AppLayout                  # 应用布局
│   ├── Navbar                 # 顶部导航栏
│   │   ├── Logo
│   │   ├── NavigationMenu
│   │   ├── UserMenu
│   │   └── NotificationBell
│   ├── Sidebar                # 侧边栏
│   │   ├── ProjectList        # 项目列表
│   │   └── QuickActions       # 快捷操作
│   ├── MainContent            # 主内容区
│   │   └── <RouterView />
│   ├── Footer                 # 底部信息
│   └── MobileBottomNav        # 移动端底部导航（<768px显示）
│       ├── NavItem [×5]       # 移动端底部导航项
└── GlobalComponents
    ├── MessageToast           # 全局消息提示
    ├── ModalContainer         # 全局模态框容器
    └── LoadingOverlay         # 全局加载遮罩
```

### 3.2 核心组件设计

#### 3.2.1 项目仪表盘组件 (ProjectDashboard.vue)

```
ProjectDashboard
├── ProjectHeader              # 项目头部信息
│   ├── ProjectTitle
│   ├── ProjectStatus
│   └── ProjectActions
├── ProgressOverview           # 进度概览
│   ├── StepProgressChart      # 16步流程进度图（ECharts）
│   ├── TaskStatsCard          # 任务统计卡片
│   └── AgentStatusCard        # Agent状态卡片
├── RecentActivities           # 最近活动
│   └── ActivityTimeline       # 活动时间线
├── QuickActions               # 快捷操作
│   ├── CreateTaskButton
│   ├── SendMessageButton
│   └── ViewReportButton
└── NotificationsPanel         # 通知面板
```

#### 3.2.2 16步流程可视化组件 (StepFlowViewer.vue)

```
StepFlowViewer
├── FlowHeader                 # 流程头部
│   ├── CurrentStepIndicator   # 当前步骤指示器
│   └── OverallProgress        # 总体进度
├── StepList                   # 步骤列表
│   └── StepItem [×16]         # 步骤项
│       ├── StepIcon           # 步骤图标
│       ├── StepTitle          # 步骤标题
│       ├── StepStatus         # 步骤状态
│       ├── StepAssignee       # 执行人
│       └── StepActions        # 步骤操作
├── StepDetail                 # 步骤详情（展开时显示）
│   ├── TaskList               # 任务列表
│   ├── QARecords              # QA检验记录
│   └── Timeline               # 执行时间线
└── FlowControls               # 流程控制
    ├── PrevStepButton
    ├── NextStepButton
    └── PauseResumeButton
```

#### 3.2.3 项目讨论群聊天组件 (GroupChat.vue)

```
GroupChat
├── ChatHeader                 # 聊天头部
│   ├── GroupName              # 群组名称
│   ├── MemberCount            # 成员数量
│   └── ModeSwitch             # 模式切换（讨论/会议）
├── MessageList                # 消息列表
│   ├── MessageItem [×N]       # 消息项
│   │   ├── Avatar             # 头像
│   │   ├── Name               # 发送者名称
│   │   ├── Timestamp          # 时间戳
│   │   ├── Content            # 消息内容
│   │   └── Actions            # 消息操作
│   └── DateSeparator          # 日期分隔符
├── MessageInput               # 消息输入区
│   ├── Textarea               # 文本输入框
│   ├── MentionDropdown        # @提及下拉框
│   ├── AttachmentUpload       # 附件上传
│   └── SendButton             # 发送按钮
├── MemberList                 # 成员列表（可收起）
│   └── MemberItem [×9]        # 成员项
│       ├── Avatar
│       ├── Name
│       └── StatusIndicator    # 状态指示器
└── MeetingControls            # 会议控制（会议模式时显示）
    ├── AgendaList             # 议程列表
    ├── Timer                  # 计时器
    └── MinutesPreview         # 纪要预览
```

#### 3.2.4 Agent状态监控组件 (AgentMonitor.vue)

```
AgentMonitor
├── MonitorHeader              # 监控头部
│   ├── Title
│   └── RefreshButton
├── AgentGrid                  # Agent网格
│   └── AgentCard [×9]         # Agent卡片
│       ├── AgentAvatar        # Agent头像
│       ├── AgentName          # Agent名称
│       ├── AgentRole          # Agent角色
│       ├── StatusBadge        # 状态徽章
│       ├── CurrentTask        # 当前任务
│       ├── LoadBar            # 负载条
│       └── ActionButtons      # 操作按钮
├── SwarmSection               # 蜂群部分
│   ├── SwarmHeader            # 蜂群头部
│   └── SwarmAgentList         # 蜂群Agent列表
│       └── SwarmAgentItem [×N]
└── ActivityFeed               # 活动动态
    └── ActivityItem [×N]
```

#### 3.2.5 QA检验记录组件 (QAInspectionRecord.vue)

```
QAInspectionRecord
├── RecordHeader               # 记录头部
│   ├── TaskName               # 任务名称
│   ├── InspectionStatus       # 检验状态
│   └── Score                  # 评分
├── DimensionList              # 检验维度列表
│   └── DimensionItem [×N]     # 维度项
│       ├── DimensionName      # 维度名称
│       ├── ScoreBar           # 评分条
│       ├── Threshold          # 合格阈值
│       ├── Status             # 达标状态
│       └── Details            # 详情
├── ProblemList                # 问题列表（不合格时显示）
│   └── ProblemItem [×N]       # 问题项
│       ├── ProblemDescription # 问题描述
│       └── Suggestion         # 修改建议
├── HistoryTab                 # 历史标签页
│   └── HistoryRecord [×N]     # 历史记录
└── Actions                    # 操作按钮
    ├── ResubmitButton         # 重新提交
    └── ExportReportButton     # 导出报告
```

---

## 4. 路由设计

### 4.1 路由结构

```typescript
const routes = [
  // 认证路由
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { public: true }
  },

  // 主应用路由
  {
    path: '/',
    component: () => import('@/views/layout/AppLayout.vue'),
    children: [
      // 仪表盘
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue')
      },

      // 项目管理
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/project/ProjectListView.vue'),
        children: [
          {
            path: ':id',
            name: 'ProjectDetail',
            component: () => import('@/views/project/ProjectDetailView.vue'),
            children: [
              { path: 'overview', name: 'ProjectOverview', component: () => import('@/views/project/tabs/OverviewTab.vue') },
              { path: 'steps', name: 'ProjectSteps', component: () => import('@/views/project/tabs/StepsTab.vue') },
              { path: 'tasks', name: 'ProjectTasks', component: () => import('@/views/project/tabs/TasksTab.vue') },
              { path: 'chat', name: 'ProjectChat', component: () => import('@/views/project/tabs/ChatTab.vue') },
              { path: 'agents', name: 'ProjectAgents', component: () => import('@/views/project/tabs/AgentsTab.vue') },
              { path: 'qa', name: 'ProjectQA', component: () => import('@/views/project/tabs/QATab.vue') },
              { path: 'reports', name: 'ProjectReports', component: () => import('@/views/project/tabs/ReportsTab.vue') }
            ]
          },
          {
            path: 'create',
            name: 'CreateProject',
            component: () => import('@/views/project/CreateProjectView.vue')
          }
        ]
      },

      // Agent管理
      {
        path: 'agents',
        name: 'Agents',
        component: () => import('@/views/agent/AgentMonitorView.vue')
      },

      // 群组管理
      {
        path: 'groups',
        name: 'Groups',
        component: () => import('@/views/group/GroupListView.vue'),
        children: [
          {
            path: ':id',
            name: 'GroupDetail',
            component: () => import('@/views/group/GroupChatView.vue')
          }
        ]
      },

      // 管理后台
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('@/views/admin/AdminLayout.vue'),
        meta: { requiresAdmin: true },
        children: [
          { path: 'users', name: 'AdminUsers', component: () => import('@/views/admin/UserManageView.vue') },
          { path: 'profiles', name: 'AdminProfiles', component: () => import('@/views/admin/ProfileManageView.vue') },
          { path: 'system', name: 'AdminSystem', component: () => import('@/views/admin/SystemConfigView.vue') },
          { path: 'logs', name: 'AdminLogs', component: () => import('@/views/admin/LogView.vue') }
        ]
      }
    ]
  },

  // 404页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/common/NotFoundView.vue')
  }
]
```

### 4.2 路由守卫

```typescript
// 认证守卫
router.beforeEach((to, from, next) => {
  const isAuthenticated = useUserStore().isAuthenticated
  const isPublic = to.meta.public

  if (!isAuthenticated && !isPublic) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

// 权限守卫
router.beforeEach((to, from, next) => {
  const userRole = useUserStore().role
  const requiresAdmin = to.meta.requiresAdmin

  if (requiresAdmin && userRole !== 'admin') {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})
```

---

## 5. 状态管理设计

### 5.1 Pinia Store 结构

#### 5.1.1 用户状态 (user.ts)

```typescript
interface UserState {
  user: UserInfo | null
  token: string | null
  isAuthenticated: boolean
  permissions: string[]
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    user: null,
    token: null,
    isAuthenticated: false,
    permissions: []
  }),
  actions: {
    async login(credentials: LoginCredentials),
    async logout(),
    async fetchUserProfile(),
    updatePermissions(permissions: string[])
  }
})
```

#### 5.1.2 项目状态 (project.ts)

```typescript
interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  projectSteps: Step[]
  tasks: Task[]
  loading: boolean
}

export const useProjectStore = defineStore('project', {
  state: (): ProjectState => ({
    projects: [],
    currentProject: null,
    projectSteps: [],
    tasks: [],
    loading: false
  }),
  actions: {
    async fetchProjects(),
    async fetchProject(id: string),
    async createProject(data: CreateProjectData),
    async updateProjectProgress(projectId: string, step: number),
    async fetchProjectSteps(projectId: string),
    async fetchTasks(projectId: string)
  }
})
```

#### 5.1.3 Agent状态 (agent.ts)

```typescript
interface AgentState {
  agents: NamedAgent[]
  swarmAgents: SwarmAgent[]
  swarms: Swarm[]
  agentActivities: Activity[]
}

export const useAgentStore = defineStore('agent', {
  state: (): AgentState => ({
    agents: [],
    swarmAgents: [],
    swarms: [],
    agentActivities: []
  }),
  actions: {
    async fetchAgents(),
    async fetchSwarmAgents(swarmId: string),
    async fetchSwarms(),
    async updateAgentStatus(agentId: string, status: AgentStatus),
    async createSwarm(data: CreateSwarmData)
  }
})
```

#### 5.1.4 群组状态 (group.ts)

```typescript
interface GroupState {
  groups: Group[]
  currentGroup: Group | null
  messages: Message[]
  members: GroupMember[]
  meetingState: MeetingState | null
}

export const useGroupStore = defineStore('group', {
  state: (): GroupState => ({
    groups: [],
    currentGroup: null,
    messages: [],
    members: [],
    meetingState: null
  }),
  actions: {
    async fetchGroups(),
    async fetchGroup(groupId: string),
    async fetchMessages(groupId: string),
    async sendMessage(groupId: string, content: string),
    async startMeeting(groupId: string, data: MeetingData),
    async stopMeeting(groupId: string)
  }
})
```

#### 5.1.5 WebSocket状态 (websocket.ts)

```typescript
interface WebSocketState {
  connection: WebSocket | null
  isConnected: boolean
  subscriptions: string[]
  messageQueue: Message[]
}

export const useWebSocketStore = defineStore('websocket', {
  state: (): WebSocketState => ({
    connection: null,
    isConnected: false,
    subscriptions: [],
    messageQueue: []
  }),
  actions: {
    connect(),
    disconnect(),
    subscribe(groupIds: string[]),
    unsubscribe(groupId: string),
    sendMessage(type: string, data: any),
    handleIncomingMessage(event: MessageEvent)
  }
})
```

---

## 6. 页面布局设计

### 6.1 主布局 (AppLayout.vue)

```
┌─────────────────────────────────────────────────────────────┐
│  Navbar (顶部导航栏)                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Logo  │ 导航菜单  │ 搜索框  │ 通知  │ 用户菜单      │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Sidebar (侧边栏)  │  MainContent (主内容区)                │
│  ┌─────────────┐   │  ┌─────────────────────────────┐     │
│  │ 项目列表    │   │  │                               │     │
│  │ ┌─────┐    │   │  │  RouterView 渲染区域          │     │
│  │ │项目1 │   │   │  │                               │     │
│  │ ├─────┤    │   │  │  根据路由动态渲染不同页面      │     │
│  │ │项目2 │   │   │  │                               │     │
│  │ ├─────┤    │   │  │                               │     │
│  │ │项目3 │   │   │  │                               │     │
│  │ └─────┘    │   │  └─────────────────────────────┘     │
│  │           │   │                                       │
│  │ 快捷操作   │   │                                       │
│  │ [创建项目] │   │                                       │
│  └─────────────┘   │                                       │
├─────────────────────────────────────────────────────────────┤
│  Footer (底部信息)                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 版本信息  │ 版权声明  │ 系统状态                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 项目详情页布局

```
┌─────────────────────────────────────────────────────────────┐
│  ProjectHeader (项目头部)                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 项目名称  │ 状态  │ 进度条  │ 操作按钮              │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Tabs (标签页导航)                                           │
│  [概览] [流程] [任务] [聊天] [Agent] [QA] [报告]          │
├─────────────────────────────────────────────────────────────┤
│  TabContent (标签页内容)                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  根据选中的标签页显示不同内容                        │   │
│  │                                                     │   │
│  │  - 概览: 项目仪表盘                                 │   │
│  │  - 流程: 16步流程可视化                             │   │
│  │  - 任务: 任务列表和管理                             │   │
│  │  - 聊天: 项目讨论群                                 │   │
│  │  - Agent: Agent状态监控                            │   │
│  │  - QA: QA检验记录                                  │   │
│  │  - 报告: 项目报告                                  │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 响应式布局

| 屏幕宽度 | 布局调整 |
|----------|----------|
| ≥1200px | 完整布局，侧边栏展开 |
| 992px-1199px | 侧边栏收缩为图标模式 |
| 768px-991px | 侧边栏隐藏，通过汉堡菜单切换 |
| <768px | 移动端布局，单列显示，底部导航 |

**移动端底部导航**: 屏幕宽度 <768px 时显示 MobileBottomNav 组件替代侧边栏，包含 5 个主要导航项：仪表盘、项目、Agent、群组、我的。

---

## 7. API接口封装

### 7.1 HTTP客户端封装 (request.ts)

```typescript
class RequestClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // 请求拦截器 - 添加认证token
    // 从localStorage读取token避免与Pinia store产生循环依赖
    // Token在登录成功后同时存储到Pinia store和localStorage
    this.instance.interceptors.request.use(config => {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // 响应拦截器 - 处理错误
    this.instance.interceptors.response.use(
      response => response.data,
      error => this.handleError(error)
    )
  }

  // GET/POST/PUT/DELETE 方法封装
  // ...
}

export const request = new RequestClient()
```

### 7.2 API模块设计

每个API模块对应一个后端功能模块：

```typescript
// api/project.ts
export const projectApi = {
  getProjects: () => request.get('/api/projects'),
  getProject: (id: string) => request.get(`/api/projects/${id}`),
  createProject: (data: CreateProjectData) => request.post('/api/projects', data),
  getProjectProgress: (id: string) => request.get(`/api/projects/${id}/progress`),
  executeStep: (id: string, step: number) => request.post(`/api/projects/${id}/step${step}`)
}

// api/agent.ts
export const agentApi = {
  getAgents: () => request.get('/api/agents'),
  getAgent: (id: string) => request.get(`/api/agents/${id}`),
  registerAgent: (data: RegisterAgentData) => request.post('/api/agents/register', data),
  getProfiles: () => request.get('/api/profiles')
}

// api/group.ts
export const groupApi = {
  getGroups: () => request.get('/api/groups'),
  getGroup: (id: string) => request.get(`/api/groups/${id}`),
  getMessages: (id: string) => request.get(`/api/groups/${id}/messages`),
  addMember: (id: string, data: AddMemberData) => request.post(`/api/groups/${id}/members`, data)
}
```

---

## 8. WebSocket实时通信

### 8.1 WebSocket客户端封装 (websocket.ts)

```typescript
// WebSocket消息类型定义
export interface WsMessage {
  type: string
  data: any
  timestamp?: number
  messageId?: string
}

class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectTimer: number | null = null
  private messageHandlers: Map<string, Function[]> = new Map()

  connect(url: string) {
    this.ws = new WebSocket(url)
    this.setupEventHandlers()
  }

  private setupEventHandlers() {
    this.ws!.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    }

    this.ws!.onmessage = (event) => {
      try {
        const message: WsMessage = JSON.parse(event.data)
        this.handleMessage(message)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    this.ws!.onclose = () => {
      console.log('WebSocket disconnected')
      this.scheduleReconnect()
    }

    this.ws!.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  subscribe(eventType: string, handler: Function) {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, [])
    }
    this.messageHandlers.get(eventType)!.push(handler)
  }

  send(type: string, data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }))
    }
  }
}

export const wsClient = new WebSocketClient()
```

### 8.2 实时消息处理

```typescript
// 订阅项目进度更新
wsClient.subscribe('project.step.completed', (data) => {
  useProjectStore().updateStepProgress(data.projectId, data.step)
})

// 订阅新消息
wsClient.subscribe('message_new', (data) => {
  useGroupStore().addMessage(data.groupId, data.message)
})

// 订阅Agent状态更新
wsClient.subscribe('agent_status', (data) => {
  useAgentStore().updateAgentStatus(data.agentId, data.status)
})
```

---

## 9. 国际化支持

### 9.1 语言包结构

```typescript
// src/locales/zh-CN.ts
export default {
  common: {
    save: '保存',
    cancel: '取消',
    delete: '删除',
    confirm: '确认'
  },
  project: {
    createProject: '创建项目',
    projectName: '项目名称',
    projectDescription: '项目描述',
    steps: '步骤',
    progress: '进度'
  },
  agent: {
    agentName: 'Agent名称',
    agentRole: 'Agent角色',
    status: '状态',
    online: '在线',
    offline: '离线',
    busy: '忙碌'
  }
}
```

### 9.2 语言切换组件

```vue
<template>
  <el-select v-model="locale" @change="changeLocale">
    <el-option label="简体中文" value="zh-CN" />
    <el-option label="English" value="en-US" />
  </el-select>
</template>

<script setup lang="ts">
const { locale, changeLocale } = useI18n()

const changeLocale = (newLocale: string) => {
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}
</script>
```

---

## 10. 无障碍访问

### 10.1 键盘导航

- Tab 键在交互元素间导航
- Enter/Space 激活按钮和链接
- Escape 关闭模态框和下拉菜单
- 箭头键在列表和选项中选择

### 10.2 屏幕阅读器支持

```vue
<template>
  <button aria-label="创建新项目" aria-describedby="project-help">
    创建项目
  </button>
  <span id="project-help" class="sr-only">
    填写项目信息以创建新的软件开发项目
  </span>
</template>
```

### 10.3 ARIA标签

```vue
<!-- 进度条 -->
<div role="progressbar" 
     aria-valuenow="{{ progress }}" 
     aria-valuemin="0" 
     aria-valuemax="100">
  {{ progress }}%
</div>

<!-- 通知区域 -->
<div aria-live="polite" aria-atomic="true">
  {{ notificationMessage }}
</div>
```

---

## 11. 构建优化

### 11.1 代码分割
- 路由级别懒加载: 所有页面组件使用 `() => import()` 动态导入
- 组件级别懒加载: Monaco Editor 等大体量组件使用 `defineAsyncComponent` 异步加载
- Vite 配置 `manualChunks` 分离 vendor 依赖

### 11.2 压缩与缓存
- 启用 gzip/brotli 压缩 (vite-plugin-compression)
- 静态资源 CDN 加速 (配置 publicPath 为 CDN 地址)
- 文件哈希命名 (Vite 默认 `[name].[hash].ext`)

### 11.3 体积优化
- Monaco Editor 按需加载语言包 (仅加载需要的语言)
- Tree-shaking 启用 (Vite 默认)
- 生产环境移除 console.log (Terser 插件)
- 目标包体积: <500KB (gzip后)

---

**文档结束**
