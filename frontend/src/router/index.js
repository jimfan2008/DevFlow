import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 认证路由
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

  // 主应用路由
  {
    path: '/',
    redirect: '/boards'
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
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true, title: '个人资料' }
  },

  // 404
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
