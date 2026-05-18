import { useAuthStore } from '@/stores/useAuthStore'

router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - DevFlow` : 'DevFlow'

  const authStore = useAuthStore()

  // 需要认证的页面
  if (to.meta.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }

  // 已登录用户访问登录/注册页，跳转到看板列表
  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    next({ name: 'BoardList' })
    return
  }

  next()
})

router.afterEach(() => {
  // 页面访问统计等
})

export default router
