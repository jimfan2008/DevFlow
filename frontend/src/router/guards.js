import router from './index'
import { useAuthStore } from '@/stores/useAuthStore'

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - DevFlow` : 'DevFlow'

  const authStore = useAuthStore()

  if (to.meta.requiresAuth !== false) {
    if (!authStore.isAuthenticated) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }

  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    next({ name: 'ProjectList' })
    return
  }

  next()
})

export default router
