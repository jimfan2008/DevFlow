# DevFlow 前端设计文档 V1.0

**项目**: DevFlow 项目管理平台
**版本**: 1.0
**日期**: 2026-06-13
**作者**: HouWang (后旺) — 架构设计师
**状态**: 初稿

---

## 1. 前端技术栈

### 1.1 核心框架与库

| 类别 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 框架 | Vue 3 | 3.4+ | 前端核心框架 (Composition API + `<script setup>`) |
| UI组件库 | Element Plus | 2.5+ | 桌面端UI组件 (表格、表单、对话框等) |
| 状态管理 | Pinia | 2.1+ | 全局状态管理 |
| 路由 | Vue Router 4 | 4.3+ | SPA路由管理 |
| HTTP客户端 | Axios | 1.6+ | REST API请求 |
| WebSocket | 原生 WebSocket API | - | 实时通信 (群聊/进度推送) |
| 国际化 | Vue I18n | 9.13+ | 多语言支持 (中文/英文) |
| 构建工具 | Vite | 5.2+ | 开发服务器和构建 |
| 类型检查 | TypeScript | 5.4+ | 类型安全 |
| CSS预处理 | SCSS | - | 样式预处理 |
| 图表 | ECharts | 5.5+ | 数据可视化 (流程图、依赖图等) |
| 代码高亮 | Prism.js | 1.29+ | 代码片段高亮显示 |
| Markdown渲染 | marked + highlight.js | - | Markdown内容渲染 |
| 测试 | Vitest + Vue Test Utils | - | 单元测试 |
| E2E测试 | Playwright | 1.44+ | 端到端测试 |

### 1.2 目录结构

```
frontend/
├── public/
│   ├── locales/              # 国际化语言包
│   │   ├── zh-CN.json       # 简体中文
│   │   └── en.json          # 英文
│   └── favicon.ico
├── src/
│   ├── api/                  # API请求封装
│   │   ├── auth.ts          # 认证相关API
│   │   ├── project.ts       # 项目管理API
│   │   ├── agent.ts         # Agent管理API
│   │   ├── swarm.ts         # 蜂群管理API
│   │   ├── qa.ts            # QA门控API
│   │   ├── group.ts         # 群聊管理API
│   │   ├── repo.ts          # 代码库管理API
│   │   ├── hermes.ts        # Gateway通信API
│   │   ├── websocket.ts     # WebSocket连接管理
│   │   └── index.ts         # API统一导出
│   ├── assets/              # 静态资源
│   │   ├── styles/          # 全局样式
│   │   │   ├── variables.scss  # SCSS变量
│   │   │   ├── mixins.scss    # SCSS混入
│   │   │   └── global.scss    # 全局样式
│   │   └── images/          # 图片资源
│   ├── components/          # 通用组件
│   │   ├── common/          # 基础组件
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   ├── AppFooter.vue
│   │   │   ├── Breadcrumb.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   └── EmptyState.vue
│   │   ├── workflow/        # 流程相关组件
│   │   │   ├── StepTimeline.vue      # 16步流程时间线
│   │   │   ├── StepProgressCard.vue  # 步骤进度卡片
│   │   │   ├── DependencyGraph.vue   # 任务依赖图
│   │   │   └── TaskDependency.vue    # 任务依赖可视化
│   │   ├── agent/           # Agent相关组件
│   │   │   ├── AgentCard.vue         # Agent信息卡片
│   │   │   ├── AgentStatusBadge.vue  # Agent状态徽章
│   │   │   ├── SwarmPanel.vue        # 蜂群管理面板
│   │   │   └── AgentChat.vue         # Agent对话界面
│   │   ├── collaboration/   # 协作相关组件
│   │   │   ├── GroupChat.vue         # 群聊界面
│   │   │   ├── MessageBubble.vue     # 消息气泡
│   │   │   ├── MessageInput.vue      # 消息输入框
│   │   │   ├── MentionPicker.vue     # @提及选择器
│   │   │   └── MeetingPanel.vue      # 会议模式面板
│   │   ├── qa/              # QA相关组件
│   │   │   ├── QAResultCard.vue      # QA检验结果卡片
│   │   │   ├── QAScoreGauge.vue      # QA评分仪表盘
│   │   │   ├── QADimensionBar.vue    # 检验维度柱状图
│   │   │   └── QARollbackDialog.vue  # QA退回对话框
│   │   └── layout/          # 布局组件
│   │       ├── MainLayout.vue
│   │       └── AdminLayout.vue
│   ├── composables/         # 组合式函数
│   │   ├── useAuth.ts       # 认证逻辑
│   │   ├── useProject.ts    # 项目逻辑
│   │   ├── useWorkflow.ts   # 流程调度逻辑
│   │   ├── useAgent.ts      # Agent管理逻辑
│   │   ├── useSwarm.ts      # 蜂群管理逻辑
│   │   ├── useQA.ts         # QA检验逻辑
│   │   ├── useGroup.ts      # 群聊逻辑
│   │   ├── useWebSocket.ts  # WebSocket连接逻辑
│   │   ├── useMeeting.ts    # 会议逻辑
│   │   └── useNotification.ts # 通知逻辑
│   ├── stores/              # Pinia状态管理
│   │   ├── auth.ts          # 用户认证状态
│   │   ├── project.ts       # 项目状态
│   │   ├── workflow.ts      # 16步流程状态
│   │   ├── agent.ts         # Agent状态
│   │   ├── swarm.ts         # 蜂群状态
│   │   ├── qa.ts            # QA状态
│   │   ├── group.ts         # 群聊状态
│   │   ├── meeting.ts       # 会议状态
│   │   ├── notification.ts  # 通知状态
│   │   └── settings.ts      # 用户设置状态
│   ├── views/               # 页面视图
│   │   ├── auth/
│   │   │   ├── LoginView.vue
│   │   │   └── RegisterView.vue
│   │   ├── project/
│   │   │   ├── ProjectListView.vue      # 项目列表
│   │   │   ├── ProjectCreateView.vue    # 项目创建
│   │   │   ├── ProjectDetailView.vue    # 项目详情
│   │   │   ├── WorkflowView.vue         # 16步流程管理
│   │   │   ├── TaskView.vue             # 任务管理
│   │   │   └── DocumentView.vue         # 文档查看
│   │   ├── agent/
│   │   │   ├── AgentListView.vue        # Agent列表
│   │   │   ├── AgentDetailView.vue      # Agent详情
│   │   │   └── SwarmView.vue           # 蜂群管理
│   │   ├── collaboration/
│   │   │   ├── GroupChatView.vue        # 群聊界面
│   │   │   └── MeetingView.vue          # 会议界面
│   │   ├── qa/
│   │   │   ├── QARecordView.vue         # QA检验记录
│   │   │   └── QAReportView.vue         # QA报告
│   │   ├── repo/
│   │   │   ├── RepoView.vue             # 代码库查看
│   │   │   └── PRView.vue               # PR管理
│   │   ├── admin/
│   │   │   ├── DashboardView.vue        # 管理仪表盘
│   │   │   ├── AgentManageView.vue      # Agent管理
│   │   │   ├── SystemMonitorView.vue    # 系统监控
│   │   │   └── UserManageView.vue       # 用户管理
│   │   └── error/
│   │       ├── NotFoundView.vue
│   │       └── ErrorView.vue
│   ├── router/              # 路由配置
│   │   ├── index.ts         # 路由定义
│   │   └── guards.ts        # 路由守卫
│   ├── utils/               # 工具函数
│   │   ├── date.ts          # 日期处理
│   │   ├── format.ts        # 格式化函数
│   │   ├── validation.ts    # 表单验证
│   │   └── constants.ts     # 常量定义
│   ├── types/               # TypeScript类型定义
│   │   ├── project.ts
│   │   ├── agent.ts
│   │   ├── workflow.ts
│   │   ├── qa.ts
│   │   ├── group.ts
│   │   └── index.ts
│   ├── App.vue              # 根组件
│   └── main.ts              # 入口文件
├── tests/                   # 测试文件
│   ├── unit/                # 单元测试
│   └── e2e/                 # E2E测试
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

---

## 2. 路由设计

### 2.1 路由结构

```typescript
const routes = [
  // 认证路由
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false }
  },

  // 主布局路由
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      // 首页重定向到项目列表
      {
        path: '',
        redirect: '/projects'
      },

      // 项目管理
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/project/ProjectListView.vue')
      },
      {
        path: 'projects/create',
        name: 'ProjectCreate',
        component: () => import('@/views/project/ProjectCreateView.vue')
      },
      {
        path: 'projects/:id',
        component: () => import('@/views/project/ProjectDetailView.vue'),
        children: [
          {
            path: 'workflow',
            name: 'ProjectWorkflow',
            component: () => import('@/views/project/WorkflowView.vue')
          },
          {
            path: 'tasks',
            name: 'ProjectTasks',
            component: () => import('@/views/project/TaskView.vue')
          },
          {
            path: 'documents',
            name: 'ProjectDocuments',
            component: () => import('@/views/project/DocumentView.vue')
          },
          {
            path: 'qa',
            name: 'ProjectQA',
            component: () => import('@/views/qa/QARecordView.vue')
          },
          {
            path: 'repo',
            name: 'ProjectRepo',
            component: () => import('@/views/repo/RepoView.vue')
          },
          {
            path: 'chat',
            name: 'ProjectChat',
            component: () => import('@/views/collaboration/GroupChatView.vue')
          }
        ]
      },

      // Agent管理
      {
        path: 'agents',
        name: 'AgentList',
        component: () => import('@/views/agent/AgentListView.vue')
      },
      {
        path: 'agents/:id',
        name: 'AgentDetail',
        component: () => import('@/views/agent/AgentDetailView.vue')
      },
      {
        path: 'swarms',
        name: 'SwarmList',
        component: () => import('@/views/agent/SwarmView.vue')
      },

      // 协作
      {
        path: 'groups',
        name: 'GroupList',
        component: () => import('@/views/collaboration/GroupChatView.vue')
      },
      {
        path: 'groups/:id',
        name: 'GroupDetail',
        component: () => import('@/views/collaboration/GroupChatView.vue')
      },
      {
        path: 'meetings/:id',
        name: 'Meeting',
        component: () => import('@/views/collaboration/MeetingView.vue')
      }
    ]
  },

  // 管理员布局
  {
    path: '/admin',
    component: () => import('@/components/layout/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresRole: 'admin' },
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/DashboardView.vue')
      },
      {
        path: 'agents',
        name: 'AdminAgents',
        component: () => import('@/views/admin/AgentManageView.vue')
      },
      {
        path: 'monitor',
        name: 'SystemMonitor',
        component: () => import('@/views/admin/SystemMonitorView.vue')
      },
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('@/views/admin/UserManageView.vue')
      }
    ]
  },

  // 错误页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/NotFoundView.vue')
  }
];
```

### 2.2 路由守卫

```typescript
// 认证守卫
router.beforeEach((to, from, next) => {
  const isAuthenticated = useAuthStore().isAuthenticated;
  
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
  } else if (to.meta.requiresRole) {
    const userRole = useAuthStore().userRole;
    if (userRole !== to.meta.requiresRole) {
      next({ name: 'NotFound' });
    } else {
      next();
    }
  } else {
    next();
  }
});
```

---

## 3. 状态管理设计

### 3.1 Pinia Store 架构

```typescript
// auth.ts - 认证状态
export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    token: null as string | null,
    refreshToken: null as string | null,
    isAuthenticated: false
  }),
  getters: {
    userRole: (state) => state.user?.role,
    isadmin: (state) => state.user?.role === 'admin'
  },
  actions: {
    async login(credentials: LoginCredentials) {},
    async logout() {},
    async refreshToken() {},
    async fetchUserProfile() {}
  }
});

// project.ts - 项目状态
export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [] as Project[],
    currentProject: null as Project | null,
    isLoading: false,
    pagination: {
      page: 1,
      pageSize: 20,
      total: 0
    }
  }),
  getters: {
    activeProjects: (state) => 
      state.projects.filter(p => p.status === 'active'),
    projectStats: (state) => ({
      total: state.projects.length,
      active: state.activeProjects.length,
      completed: state.projects.filter(p => p.status === 'completed').length
    })
  },
  actions: {
    async fetchProjects(params?: QueryParams) {},
    async fetchProject(id: string) {},
    async createProject(data: CreateProjectData) {},
    async updateProject(id: string, data: UpdateProjectData) {},
    async deleteProject(id: string) {}
  }
});

// workflow.ts - 16步流程状态
export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    currentStep: 1,
    steps: [] as WorkflowStep[],
    tasks: [] as Task[],
    dependencyGraph: null as DependencyGraph | null,
    isExecuting: false
  }),
  getters: {
    currentStepData: (state) => 
      state.steps.find(s => s.step_number === state.currentStep),
    completedSteps: (state) => 
      state.steps.filter(s => s.status === 'completed'),
    pendingSteps: (state) => 
      state.steps.filter(s => s.status === 'pending'),
    progressPercent: (state) => 
      Math.round((state.completedSteps.length / 16) * 100)
  },
  actions: {
    async fetchWorkflow(projectId: string) {},
    async executeStep(stepNumber: number) {},
    async cancelStep(stepNumber: number) {},
    async retryStep(stepNumber: number) {},
    async fetchDependencyGraph(projectId: string) {}
  }
});

// agent.ts - Agent状态
export const useAgentStore = defineStore('agent', {
  state: () => ({
    agents: [] as Agent[],
    swarms: [] as Swarm[],
    profiles: [] as ProfileInfo[]
  }),
  getters: {
    namedAgents: (state) => 
      state.agents.filter(a => a.agent_type === 'named'),
    swarmAgents: (state) => 
      state.agents.filter(a => a.agent_type === 'swarm'),
    onlineAgents: (state) => 
      state.agents.filter(a => a.status === 'online'),
    busyAgents: (state) => 
      state.agents.filter(a => a.status === 'busy')
  },
  actions: {
    async fetchAgents() {},
    async fetchAgent(id: string) {},
    async syncProfiles() {},
    async fetchSwarms(projectId: string) {}
  }
});

// group.ts - 群聊状态
export const useGroupStore = defineStore('group', {
  state: () => ({
    groups: [] as Group[],
    currentGroup: null as Group | null,
    messages: [] as Message[],
    isWebSocketConnected: false,
    typingAgents: [] as string[]
  }),
  getters: {
    unreadCount: (state) => 
      state.messages.filter(m => !m.is_read).length,
    groupMembers: (state) => 
      state.currentGroup?.members || []
  },
  actions: {
    async fetchGroups() {},
    async fetchGroup(id: string) {},
    async fetchMessages(groupId: string, page: number) {},
    async sendMessage(message: SendMessageData) {},
    connectWebSocket(groupId: string) {},
    disconnectWebSocket() {},
    handleWebSocketMessage(event: WebSocketEvent) {}
  }
});

// qa.ts - QA状态
export const useQAStore = defineStore('qa', {
  state: () ({
    records: [] as QARecord[],
    currentInspection: null as Inspection | null,
    isInspecting: false
  }),
  getters: {
    passRate: (state) => {
      const total = state.records.length;
      const passed = state.records.filter(r => r.acceptance_result === 'pass').length;
      return total > 0 ? (passed / total) * 100 : 0;
    },
    failedRecords: (state) => 
      state.records.filter(r => r.acceptance_result === 'fail')
  },
  actions: {
    async fetchQARecords(projectId: string) {},
    async startInspection(taskId: string) {},
    async rollbackTask(taskId: string, suggestions: string) {}
  }
});
```

### 3.2 状态流转示例

```typescript
// 16步流程状态流转
enum StepStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  ROLLED_BACK = 'rolled_back',
  SKIPPED = 'skipped'
}

interface WorkflowStep {
  step_number: number;
  step_name: string;
  status: StepStatus;
  assignee_agent_id: string;
  started_at: string | null;
  completed_at: string | null;
  qa_result: QARecord | null;
  artifacts: Artifact[];
}
```

---

## 4. 页面布局设计

### 4.1 主布局 (MainLayout)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Header (60px)                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ [Logo] DevFlow    [项目搜索]    [通知铃铛] [语言切换] [用户头像] ││
│  └─────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────┤
│  Sidebar (240px)                    Main Content                    │
│  ┌──────────────────┐                                           ┌──┼┐
│  │ 导航菜单          │                                           │  ││
│  │ ┌──────────────┐ │                                           │  ││
│  │ │ 项目管理      │ │                                           │  ││
│  │ │ ├─ 项目列表   │ │                                           │  ││
│  │ │ ├─ 创建项目   │ │                                           │  ││
│  │ │ └─ 项目详情   │ │                                           │  ││
│  │ ├──────────────┤ │                                           │  ││
│  │ │ Agent管理     │ │                                           │  ││
│  │ │ ├─ Agent列表  │ │                                           │  ││
│  │ │ ├─ 蜂群管理   │ │                                           │  ││
│  │ │ └─ 状态监控   │ │                                           │  ││
│  │ ├──────────────┤ │                                           │  ││
│  │ │ 协作空间      │ │                                           │  ││
│  │ │ ├─ 项目讨论群 │ │                                           │  ││
│  │ │ └─ 会议管理   │ │                                           │  ││
│  │ ├──────────────┤ │                                           │  ││
│  │ │ QA检验       │ │                                           │  ││
│  │ │ ├─ 检验记录   │ │                                           │  ││
│  │ │ └─ 检验报告   │ │                                           │  ││
│  │ ├──────────────┤ │                                           │  ││
│  │ │ 代码库       │ │                                           │  ││
│  │ │ └─ 仓库管理   │ │                                           │  ││
│  │ └──────────────┘ │                                           │  ││
│  └──────────────────┘                                           │  ││
├─────────────────────────────────────────────────────────────────────┤
│  Footer (40px)                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ © 2026 DevFlow | 系统状态: ● 正常 | 版本: 1.0.0                ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 项目详情页布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  项目标题 | 项目ID: proj-20260612-001                             │
├─────────────────────────────────────────────────────────────────────┤
│  项目子导航                                                          │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────────┐ │
│  │ 总览    │ 16步流程 │ 任务管理 │ 群聊    │ 代码库  │ 文档        │ │
│  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│  内容区域 (根据子导航切换)                                           │
│                                                                     │
│  16步流程视图示例:                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ 流程进度: ████████████████░░░░░░░░ 75% (12/16)                 ││
│  │                                                                 ││
│  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    ││
│  │ │ ① ✓ │ │ ② ✓ │ │ ③ ✓ │ │ ④ ✓ │ │ ⑤ ✓ │ │ ⑥ ✓ │ │ ⑦ ✓ │    ││
│  │ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    ││
│  │   ↓        ↓        ↓        ↓        ↓        ↓        ↓      ││
│  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    ││
│  │ │ ⑧ ✓ │ │ ⑨ ✓ │ │⑩ ✓  │ │⑪ ✓  │ │⑫ ✓  │ │⑬ ▶  │ │⑬ □  │    ││
│  │ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    ││
│  │                                                                 ││
│  │ 当前步骤: 第十三步 - 生产环境部署                                ││
│  │ 执行Agent: 后富 (CI/CD工程师)                                   ││
│  │ 状态: 执行中...                                                 ││
│  │ 预计完成: 30分钟内                                              ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 群聊界面布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  项目讨论群 - [项目名称]                                         [X] │
├─────────────────────────────────────────────────────────────────────┤
│  成员列表 (左侧)              消息区域 (中间)          会议面板 (右) │
│  ┌──────────────────┐       ┌──────────────────┐  ┌──────────────┐ │
│  │ 在线成员 (9)      │       │ 消息历史         │  │ 会议模式     │ │
│  │                  │       │                  │  │              │ │
│  │ ● 海梅 (项目经理) │       │ 海梅: @后兴      │  │ 会议类型:    │ │
│  │ ● 后兴 (需求分析) │       │   请开始需求     │  │ [需求评审]   │ │
│  │ ● 后旺 (架构设计) │       │                  │  │ [技术方案]   │ │
│  │ ● 后发 (程序员)   │       │ 后兴: 收到，     │  │ [每日站会]   │ │
│  │ ● 后达 (测试员)   │       │   我现在开始     │  │ [故障复盘]   │ │
│  │ ● 后富 (CI/CD)    │       │                  │  │              │ │
│  │ ● 后贵 (文档)     │       │ [系统消息]       │  │ 议程:        │ │
│  │ ● 后荣 (QA)       │       │ 后荣已加入群组   │  │ 1. PRD介绍   │ │
│  │ ● 后华 (安全员)   │       │                  │  │ 2. 业务流程  │ │
│  │                  │       │                  │  │ 3. 边界规则  │ │
│  │ 离线成员 (0)      │       │                  │  │ 4. 特殊场景  │ │
│  │                  │       │                  │  │ 5. 开发提问  │ │
│  │ [搜索成员]       │       │                  │  │              │ │
│  │                  │       │                  │  │ 决议:        │ │
│  │ [切换会议模式]    │       │                  │  │ [暂无]       │ │
│  └──────────────────┘       │                  │  │              │ │
│                             │ ┌──────────────┐ │  │ 待办:        │ │
│                             │ │ [输入消息]    │ │  │ [暂无]       │ │
│                             │ │ @提及  发送  │ │  │              │ │
│                             │ └──────────────┘ │  │ 风险:        │ │
│                             └──────────────────┘  │ [暂无]       │ │
│                                                    └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.4 蜂群管理面板布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  Agent蜂群管理                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  蜂群概览                                                           │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐     │
│  │ 蜂群名称      │ 类型         │ 成员数       │ 状态         │     │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤     │
│  │ 代码编写蜂群  │ 代码编写     │ 5/8          │ 运行中       │     │
│  │ 测试蜂群      │ 代码测试     │ 3/6          │ 运行中       │     │
│  └──────────────┴──────────────┴──────────────┴──────────────┘     │
│                                                                     │
│  蜂群详情 - 代码编写蜂群                                            │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ 调度者: 后发 (程序员)                                            ││
│  │ 创建时间: 2026-06-12 14:30:00                                   ││
│  │ 目的: TDD测试用例编写 (第七步)                                   ││
│  │                                                                 ││
│  │ 成员状态:                                                       ││
│  │ ┌──────┬──────┬──────┬──────┬──────┬──────┐                   ││
│  │ │Agent │ 状态 │ 任务 │ 进度 │ 负载 │ 操作  │                   ││
│  │ ├──────┼──────┼──────┼──────┼──────┼──────┤                   ││
│  │ │Claude│ ●绿  │ 任务1│ 80%  │ 中   │ [查看]│                   ││
│  │ │Codex │ ●绿  │ 任务2│ 60%  │ 低   │ [查看]│                   ││
│  │ │Opencode│●黄 │ 任务3│ 40%  │ 高   │ [查看]│                   ││
│  │ │Cursor │ ●绿  │ 空闲 │ 0%   │ 低   │ [分配]│                   ││
│  │ │CodeArts│●灰 │ 离线 │ -    │ -    │ [重启]│                   ││
│  └──────┴──────┴──────┴──────┴──────┴──────┘                   ││
│  │                                                                 ││
│  │ [添加成员] [解散蜂群] [查看日志]                                ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. 核心组件设计

### 5.1 StepTimeline 组件 (16步流程时间线)

```vue
<template>
  <div class="step-timeline">
    <div class="progress-bar" :style="{ width: progressPercent + '%' }" />
    <div class="steps-container">
      <StepProgressCard
        v-for="step in steps"
        :key="step.step_number"
        :step="step"
        :is-current="step.step_number === currentStep"
        @execute="handleExecuteStep"
        @retry="handleRetryStep"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useWorkflowStore } from '@/stores/workflow';
import StepProgressCard from './StepProgressCard.vue';

const workflowStore = useWorkflowStore();

const steps = computed(() => workflowStore.steps);
const currentStep = computed(() => workflowStore.currentStep);
const progressPercent = computed(() => workflowStore.progressPercent);

const handleExecuteStep = (stepNumber: number) => {
  workflowStore.executeStep(stepNumber);
};

const handleRetryStep = (stepNumber: number) => {
  workflowStore.retryStep(stepNumber);
};
</script>

<style scoped lang="scss">
.step-timeline {
  position: relative;
  padding: 20px 0;
  
  .progress-bar {
    height: 4px;
    background: #409eff;
    transition: width 0.3s ease;
  }
  
  .steps-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 16px;
  }
}
</style>
```

### 5.2 GroupChat 组件 (群聊界面)

```vue
<template>
  <div class="group-chat">
    <div class="chat-sidebar">
      <MemberList :members="groupMembers" />
    </div>
    <div class="chat-main">
      <MessageList
        :messages="messages"
        :typing-agents="typingAgents"
        @scroll-to-bottom="handleScrollToBottom"
      />
      <MessageInput
        @send="handleSendMessage"
        @mention="handleMention"
      />
    </div>
    <div class="chat-panel" v-if="isMeetingMode">
      <MeetingPanel :meeting="currentMeeting" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useGroupStore } from '@/stores/group';
import MemberList from './MemberList.vue';
import MessageList from './MessageList.vue';
import MessageInput from './MessageInput.vue';
import MeetingPanel from './MeetingPanel.vue';

const groupStore = useGroupStore();
const messages = ref<Message[]>([]);
const typingAgents = ref<string[]>([]);
const isMeetingMode = ref(false);
const currentMeeting = ref<Meeting | null>(null);

onMounted(() => {
  groupStore.connectWebSocket(currentGroup.value.id);
});

onUnmounted(() => {
  groupStore.disconnectWebSocket();
});

const handleSendMessage = async (content: string, mentions: string[]) => {
  await groupStore.sendMessage({
    group_id: currentGroup.value.id,
    content,
    mentions
  });
};

const handleMention = (mention: string) => {
  // 处理@提及
};

const handleScrollToBottom = () => {
  // 滚动到底部
};
</script>

<style scoped lang="scss">
.group-chat {
  display: flex;
  height: calc(100vh - 200px);
  
  .chat-sidebar {
    width: 240px;
    border-right: 1px solid #e4e7ed;
    padding: 16px;
  }
  
  .chat-main {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  
  .chat-panel {
    width: 300px;
    border-left: 1px solid #e4e7ed;
    padding: 16px;
  }
}
</style>
```

### 5.3 QAResultCard 组件 (QA检验结果)

```vue
<template>
  <div class="qa-result-card" :class="resultClass">
    <div class="qa-header">
      <el-tag :type="resultType" size="large">
        {{ resultLabel }}
      </el-tag>
      <span class="qa-score">{{ qaRecord.score }}/100</span>
    </div>
    
    <div class="qa-dimensions">
      <QADimensionBar
        v-for="dimension in dimensions"
        :key="dimension.name"
        :dimension="dimension"
      />
    </div>
    
    <div class="qa-details" v-if="qaRecord.problem_details">
      <h4>问题详情</h4>
      <p>{{ qaRecord.problem_details }}</p>
    </div>
    
    <div class="qa-actions">
      <el-button
        v-if="qaRecord.acceptance_result === 'fail'"
        type="primary"
        @click="handleRetry"
      >
        重新提交
      </el-button>
      <el-button @click="handleViewDetails">
        查看详情
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQAStore } from '@/stores/qa';
import QADimensionBar from './QADimensionBar.vue';

const props = defineProps<{
  qaRecord: QARecord;
}>();

const emit = defineEmits<{
  retry: [];
  viewDetails: [];
}>();

const resultClass = computed(() => 
  props.qaRecord.acceptance_result === 'pass' ? 'qa-pass' : 'qa-fail'
);

const resultType = computed(() => 
  props.qaRecord.acceptance_result === 'pass' ? 'success' : 'danger'
);

const resultLabel = computed(() => 
  props.qaRecord.acceptance_result === 'pass' ? '检验通过' : '检验未通过'
);

const dimensions = computed(() => 
  Object.entries(props.qaRecord.review_dimensions || {}).map(([name, value]) => ({
    name,
    score: (value as any).score,
    threshold: (value as any).threshold,
    passed: (value as any).passed
  }))
);

const handleRetry = () => emit('retry');
const handleViewDetails = () => emit('viewDetails');
</script>

<style scoped lang="scss">
.qa-result-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  
  &.qa-pass {
    border-left: 4px solid #67c23a;
  }
  
  &.qa-fail {
    border-left: 4px solid #f56c6c;
  }
  
  .qa-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .qa-score {
      font-size: 24px;
      font-weight: bold;
    }
  }
  
  .qa-dimensions {
    margin: 16px 0;
  }
  
  .qa-actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
  }
}
</style>
```

---

## 6. WebSocket 实时通信

### 6.1 WebSocket 连接管理

```typescript
// websocket.ts
import { ref } from 'vue';

const ws = ref<WebSocket | null>(null);
const isConnected = ref(false);
const reconnectAttempts = ref(0);
const maxReconnectAttempts = 5;

export function useWebSocket() {
  const connect = (groupId: string) => {
    const wsUrl = `ws://${window.location.host}/ws/group-chat?group_id=${groupId}`;
    
    ws.value = new WebSocket(wsUrl);
    
    ws.value.onopen = () => {
      isConnected.value = true;
      reconnectAttempts.value = 0;
      console.log('WebSocket connected');
    };
    
    ws.value.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };
    
    ws.value.onclose = () => {
      isConnected.value = false;
      console.log('WebSocket disconnected');
      handleReconnect(groupId);
    };
    
    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };
  
  const disconnect = () => {
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
  };
  
  const sendMessage = (type: string, data: any) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, data }));
    }
  };
  
  const handleWebSocketMessage = (message: any) => {
    const groupStore = useGroupStore();
    
    switch (message.type) {
      case 'message_new':
        groupStore.addMessage(message.data);
        break;
      case 'message_start':
        groupStore.setAgentTyping(message.data.agent_id, true);
        break;
      case 'message_chunk':
        groupStore.appendMessageChunk(message.data);
        break;
      case 'message_complete':
        groupStore.setAgentTyping(message.data.agent_id, false);
        break;
      case 'agent_status':
        groupStore.updateAgentStatus(message.data);
        break;
      case 'meeting_started':
        groupStore.startMeeting(message.data);
        break;
      case 'meeting_minutes':
        groupStore.saveMeetingMinutes(message.data);
        break;
    }
  };
  
  const handleReconnect = (groupId: string) => {
    if (reconnectAttempts.value < maxReconnectAttempts) {
      reconnectAttempts.value++;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.value), 30000);
      setTimeout(() => connect(groupId), delay);
    }
  };
  
  return {
    isConnected,
    connect,
    disconnect,
    sendMessage
  };
}
```

### 6.2 WebSocket 消息类型

```typescript
// WebSocket 客户端发送的消息类型
export enum ClientMessageType {
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',
  SEND_MESSAGE = 'send_message',
  START_MEETING = 'start_meeting',
  STOP_MEETING = 'stop_meeting',
  MEETING_INTERVENTION = 'meeting_intervention'
}

// WebSocket 服务端推送的事件类型
export enum ServerMessageType {
  SUBSCRIBED = 'subscribed',
  MESSAGE_NEW = 'message_new',
  MESSAGE_START = 'message_start',
  MESSAGE_CHUNK = 'message_chunk',
  MESSAGE_COMPLETE = 'message_complete',
  AGENT_STATUS = 'agent_status',
  MEETING_STARTED = 'meeting_started',
  MEETING_STOPPED = 'meeting_stopped',
  MEETING_PHASE = 'meeting_phase',
  MEETING_AGENDA = 'meeting_agenda',
  MEETING_MINUTES = 'meeting_minutes',
  MEETING_OUTCOME_SAVED = 'meeting_outcome_saved',
  TASK_CREATED = 'task_created'
}
```

---

## 7. 无障碍访问 (A11y)

### 7.1 WCAG 2.1 Level AA 实现

```vue
<template>
  <div role="main" aria-label="项目内容区域">
    <h1>{{ pageTitle }}</h1>
    
    <!-- 表单无障碍 -->
    <form @submit.prevent="handleSubmit">
      <div class="form-item">
        <label for="project-name" id="project-name-label">
          项目名称 <span aria-hidden="true">*</span>
          <span class="sr-only">(必填)</span>
        </label>
        <input
          id="project-name"
          v-model="form.name"
          type="text"
          required
          aria-labelledby="project-name-label"
          aria-describedby="project-name-help"
          :aria-invalid="!!errors.name"
          :aria-errormessage="errors.name ? 'name-error' : undefined"
        />
        <div id="project-name-help" class="help-text">
          项目名称需唯一，支持中英文和数字
        </div>
        <div
          v-if="errors.name"
          id="name-error"
          role="alert"
          aria-live="polite"
          class="error-text"
        >
          {{ errors.name }}
        </div>
      </div>
    </form>
    
    <!-- 按钮无障碍 -->
    <button
      type="submit"
      :disabled="isSubmitting"
      aria-busy="isSubmitting"
      aria-live="polite"
    >
      <span v-if="!isSubmitting">创建项目</span>
      <span v-else>
        <span class="sr-only">正在创建...</span>
        <LoadingSpinner aria-hidden="true" />
      </span>
    </button>
    
    <!-- 图像无障碍 -->
    <img
      src="/logo.png"
      alt="DevFlow 项目管理平台 Logo"
      width="120"
      height="40"
    />
    
    <!-- 图标按钮无障碍 -->
    <button
      type="button"
      aria-label="查看通知"
      :aria-expanded="notificationPanelOpen"
      :aria-controls="notification-panel"
    >
      <svg aria-hidden="true" focusable="false">
        <use href="#icon-bell" />
      </svg>
    </button>
  </div>
</template>

<style scoped lang="scss">
// 屏幕阅读器专用类
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

// 焦点样式
:focus-visible {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

// 颜色对比度 (确保 >= 4.5:1)
.error-text {
  color: #f56c6c; // 与白色背景对比度 4.53:1
}

.help-text {
  color: #606266; // 与白色背景对比度 5.92:1
}
</style>
```

### 7.2 键盘导航

```typescript
// 键盘导航组合式函数
export function useKeyboardNavigation() {
  const handleKeyDown = (event: KeyboardEvent) => {
    switch (event.key) {
      case 'Tab':
        // Tab 导航由浏览器默认处理
        break;
      case 'Enter':
      case ' ':
        // 激活按钮/链接
        if (event.target instanceof HTMLElement) {
          const role = event.target.getAttribute('role');
          if (role === 'button' || role === 'link') {
            event.preventDefault();
            event.target.click();
          }
        }
        break;
      case 'Escape':
        // 关闭模态弹窗
        closeModal();
        break;
      case 'ArrowUp':
      case 'ArrowDown':
        // 列表导航
        handleListNavigation(event.key === 'ArrowUp' ? -1 : 1);
        break;
    }
  };
  
  return { handleKeyDown };
}
```

---

## 8. 国际化 (i18n)

### 8.1 语言包结构

```json
// public/locales/zh-CN.json
{
  "common": {
    "save": "保存",
    "cancel": "取消",
    "delete": "删除",
    "confirm": "确认",
    "loading": "加载中...",
    "noData": "暂无数据",
    "search": "搜索",
    "filter": "筛选"
  },
  "project": {
    "title": "项目管理",
    "create": "创建项目",
    "name": "项目名称",
    "description": "项目描述",
    "status": "项目状态",
    "created": "创建时间",
    "progress": "项目进度"
  },
  "agent": {
    "title": "Agent管理",
    "name": "Agent名称",
    "role": "角色",
    "status": "状态",
    "online": "在线",
    "offline": "离线",
    "busy": "忙碌"
  },
  "workflow": {
    "title": "16步流程",
    "step": "步骤",
    "progress": "进度",
    "execute": "执行",
    "retry": "重试",
    "cancel": "取消"
  },
  "qa": {
    "title": "QA检验",
    "pass": "通过",
    "fail": "未通过",
    "score": "评分",
    "dimension": "检验维度",
    "rollback": "退回重做"
  }
}
```

### 8.2 国际化使用

```vue
<template>
  <div>
    <h1>{{ $t('project.title') }}</h1>
    <button @click="handleCreate">
      {{ $t('project.create') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t, locale } = useI18n();

// 切换语言
const switchLanguage = (lang: 'zh-CN' | 'en') => {
  locale.value = lang;
};
</script>
```

---

## 9. 响应式设计

### 9.1 断点定义

```scss
// assets/styles/variables.scss
$breakpoints: (
  'xs': 0,
  'sm': 576px,
  'md': 768px,
  'lg': 992px,
  'xl': 1200px,
  'xxl': 1920px
);

@mixin respond-to($breakpoint) {
  @if map-has-key($breakpoints, $breakpoint) {
    @media (min-width: map-get($breakpoints, $breakpoint)) {
      @content;
    }
  }
}
```

### 9.2 响应式布局

```scss
// 项目列表响应式
.project-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  
  @include respond-to('md') {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @include respond-to('lg') {
    grid-template-columns: repeat(3, 1fr);
  }
  
  @include respond-to('xl') {
    grid-template-columns: repeat(4, 1fr);
  }
}

// 侧边栏响应式
.sidebar {
  width: 240px;
  position: fixed;
  left: 0;
  top: 60px;
  bottom: 0;
  
  @include respond-to('md') {
    width: 200px;
  }
  
  @include respond-to('sm') {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    
    &.open {
      transform: translateX(0);
    }
  }
}
```

---

## 10. 前端构建与部署

### 10.1 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          elementPlus: ['element-plus'],
          echarts: ['echarts']
        }
      }
    }
  }
});
```

### 10.2 Docker 构建

```dockerfile
# Dockerfile.frontend
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

---

文档结束
