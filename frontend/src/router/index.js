import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false, title: '注册' }
  },

  {
    path: '/',
    redirect: '/projects'
  },

  {
    path: '/projects',
    name: 'ProjectList',
    component: () => import('@/views/ProjectListView.vue'),
    meta: { requiresAuth: true, title: '项目管理' }
  },
  {
    path: '/projects/:projectId',
    name: 'ProjectDetail',
    component: () => import('@/views/ProjectDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: '项目详情' }
  },

  {
    path: '/agents',
    name: 'AgentList',
    component: () => import('@/views/AgentListView.vue'),
    meta: { requiresAuth: true, title: 'Agent管理' }
  },
  {
    path: '/agents/:agentId',
    name: 'AgentDetail',
    component: () => import('@/views/AgentDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: 'Agent详情' }
  },

  {
    path: '/skills',
    name: 'SkillManagement',
    component: () => import('@/views/SkillView.vue'),
    meta: { requiresAuth: true, title: 'Skill管理' }
  },

  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true, title: '群聊与会议' }
  },

  {
    path: '/boards',
    name: 'BoardList',
    component: () => import('@/views/BoardListView.vue'),
    meta: { requiresAuth: true, title: '看板列表' }
  },
  {
    path: '/boards/:boardId',
    name: 'BoardDetail',
    component: () => import('@/views/BoardView.vue'),
    props: true,
    meta: { requiresAuth: true, title: '看板详情' }
  },
  {
    path: '/boards/:boardId/tasks/:taskId',
    name: 'TaskDetail',
    component: () => import('@/views/TaskDetailView.vue'),
    props: true,
    meta: { requiresAuth: true, title: '任务详情' }
  },
  {
    path: '/task-board',
    name: 'TaskBoard',
    component: () => import('@/views/TaskBoardView.vue'),
    meta: { requiresAuth: true, title: '任务看板' }
  },

  {
    path: '/repos',
    name: 'Repos',
    component: () => import('@/views/RepoView.vue'),
    meta: { requiresAuth: true, title: '代码仓库' }
  },

  {
    path: '/acceptance',
    name: 'Acceptance',
    component: () => import('@/views/AcceptanceView.vue'),
    meta: { requiresAuth: true, title: '验收报告' }
  },
  {
    path: '/notifications',
    name: 'NotificationCenter',
    component: () => import('@/views/NotificationCenterView.vue'),
    meta: { requiresAuth: true, title: '通知中心' }
  },
  {
    path: '/delivery',
    name: 'Delivery',
    component: () => import('@/views/DeliveryView.vue'),
    meta: { requiresAuth: true, title: '项目交付' }
  },

  {
    path: '/inbox',
    name: 'Inbox',
    component: () => import('@/views/InboxView.vue'),
    meta: { requiresAuth: true, title: '收件箱' }
  },
  {
    path: '/requirements',
    name: 'Requirements',
    component: () => import('@/views/RequirementsView.vue'),
    meta: { requiresAuth: true, title: '需求管理' }
  },
  {
    path: '/step2/:projectId',
    name: 'Step2',
    component: () => import('@/views/Step2View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第二步：确认核心目标与搭建组织架构' }
  },
  {
    path: '/step3/:projectId',
    name: 'Step3',
    component: () => import('@/views/Step3View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第三步：需求分析' }
  },
  {
    path: '/step4/:projectId',
    name: 'Step4',
    component: () => import('@/views/Step4View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第四步：架构设计' }
  },

  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true, title: '个人资料' }
  },

  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '404 - 页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0 }
  }
})

export default router
