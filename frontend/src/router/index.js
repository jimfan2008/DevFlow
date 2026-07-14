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
    path: '/step3/:projectId/qa',
    name: 'Step3Qa',
    component: () => import('@/views/Step3QaView.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第三步：QA检验' }
  },
  {
    path: '/step4/:projectId',
    name: 'Step4',
    component: () => import('@/views/Step4View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第四步：架构设计' }
  },
  {
    path: '/step1/:projectId',
    name: 'Step1',
    component: () => import('@/views/Step1View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第一步：项目概览' }
  },
  {
    path: '/step5/:projectId',
    name: 'Step5',
    component: () => import('@/views/Step5View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第五步：建立开发环境' }
  },
  {
    path: '/step6/:projectId',
    name: 'Step6',
    component: () => import('@/views/Step6View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第六步：制订TDD测试用例计划' }
  },
  {
    path: '/step7/:projectId',
    name: 'Step7',
    component: () => import('@/views/Step7View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第七步：编写TDD测试用例' }
  },
  {
    path: '/step8/:projectId',
    name: 'Step8',
    component: () => import('@/views/Step8View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第八步：制订代码编写计划' }
  },
  {
    path: '/step9/:projectId',
    name: 'Step9',
    component: () => import('@/views/Step9View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第九步：编写功能代码' }
  },
  {
    path: '/step10/:projectId',
    name: 'Step10',
    component: () => import('@/views/Step10View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十步：部署到测试环境' }
  },
  {
    path: '/step11/:projectId',
    name: 'Step11',
    component: () => import('@/views/Step11View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十一步：全面测试' }
  },
  {
    path: '/step12/:projectId',
    name: 'Step12',
    component: () => import('@/views/Step12View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十二步：安全审计' }
  },
  {
    path: '/step13/:projectId',
    name: 'Step13',
    component: () => import('@/views/Step13View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十三步：部署到生产环境' }
  },
  {
    path: '/step14/:projectId',
    name: 'Step14',
    component: () => import('@/views/Step14View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十四步：完善项目文档' }
  },
  {
    path: '/step15/:projectId',
    name: 'Step15',
    component: () => import('@/views/Step15View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十五步：报告交付成果' }
  },
  {
    path: '/step16/:projectId',
    name: 'Step16',
    component: () => import('@/views/Step16View.vue'),
    props: true,
    meta: { requiresAuth: true, title: '第十六步：用户满意度确认与迭代' }
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

router.beforeEach(async (to, from, next) => {
  if (to.name === 'Step3') {
    try {
      const token = localStorage.getItem('access_token') || ''
      const resp = await fetch('/api/v1/workflow/' + to.params.projectId + '/status', {
        headers: { 'Authorization': 'Bearer ' + token },
      })
      const json = await resp.json()
      const d = json && (json.data || json)
      if (d && d.steps && d.steps['3'] && d.steps['3'].status === 'qa_review' && to.query.force !== '1') {
        next({ name: 'Step3Qa', params: { projectId: to.params.projectId } })
        return
      }
    } catch (_) {}
  }
  next()
})

export default router
