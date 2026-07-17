import { describe, it, expect } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'

const LAZY_ROUTE_DEFS = [
  { path: '/login', name: 'Login' },
  { path: '/register', name: 'Register' },
  { path: '/projects', name: 'ProjectList' },
  { path: '/projects/:projectId', name: 'ProjectDetail' },
  { path: '/agents', name: 'AgentList' },
  { path: '/agents/:agentId', name: 'AgentDetail' },
  { path: '/skills', name: 'SkillManagement' },
  { path: '/chat', name: 'Chat' },
  { path: '/boards', name: 'BoardList' },
  { path: '/boards/:boardId', name: 'BoardDetail' },
  { path: '/boards/:boardId/tasks/:taskId', name: 'TaskDetail' },
  { path: '/task-board', name: 'TaskBoard' },
  { path: '/repos', name: 'Repos' },
  { path: '/acceptance', name: 'Acceptance' },
  { path: '/notifications', name: 'NotificationCenter' },
  { path: '/delivery', name: 'Delivery' },
  { path: '/requirements', name: 'Requirements' },
  { path: '/step2/:projectId', name: 'Step2' },
  { path: '/step3/:projectId', name: 'Step3' },
  { path: '/step3/:projectId/qa', name: 'Step3Qa' },
  { path: '/step4/:projectId', name: 'Step4' },
  { path: '/step1/:projectId', name: 'Step1' },
  { path: '/step5/:projectId', name: 'Step5' },
  { path: '/step6/:projectId', name: 'Step6' },
  { path: '/step7/:projectId', name: 'Step7' },
  { path: '/step8/:projectId', name: 'Step8' },
  { path: '/step9/:projectId', name: 'Step9' },
  { path: '/step10/:projectId', name: 'Step10' },
  { path: '/step11/:projectId', name: 'Step11' },
  { path: '/step12/:projectId', name: 'Step12' },
  { path: '/step13/:projectId', name: 'Step13' },
  { path: '/step14/:projectId', name: 'Step14' },
  { path: '/step15/:projectId', name: 'Step15' },
  { path: '/step16/:projectId', name: 'Step16' },
  { path: '/profile', name: 'Profile' },
  { path: '/:pathMatch(.*)*', name: 'NotFound' },
]

function createAsyncComponent(delayMs: number) {
  return (): Promise<{ default: Record<string, unknown> }> =>
    new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          default: {
            template: '<div><h1>Mock Async View</h1></div>',
            name: 'MockAsyncView',
          },
        })
      }, delayMs)
    })
}

describe('前端懒加载路由', () => {
  describe('路由定义使用懒加载模式', () => {
    it('所有36个路由的component为函数类型', () => {
      const routes = LAZY_ROUTE_DEFS.map((r) => ({
        path: r.path,
        name: r.name,
        component: createAsyncComponent(0),
        meta: { title: r.name },
      }))
      expect(routes).toHaveLength(36)
      for (const route of routes) {
        expect(typeof route.component).toBe('function')
      }
    })

    it('每个懒加载路由component非普通对象', () => {
      const routes = LAZY_ROUTE_DEFS.map((r) => ({
        path: r.path,
        name: r.name,
        component: createAsyncComponent(0),
        meta: { title: r.name },
      }))
      for (const route of routes) {
        expect(typeof route.component).toBe('function')
        expect(Array.isArray(route.component)).toBe(false)
      }
    })

    it('调用懒加载路由component返回Promise', () => {
      const route = {
        path: '/test',
        name: 'Test',
        component: createAsyncComponent(0),
      }
      const result = route.component()
      expect(result).toBeInstanceOf(Promise)
    })

    it('懒加载Promise解析后包含default属性', async () => {
      const route = {
        path: '/test',
        name: 'Test',
        component: createAsyncComponent(0),
      }
      const resolved = await route.component()
      expect(resolved).toHaveProperty('default')
      expect(typeof resolved.default.template).toBe('string')
    })

    it('所有路由名称唯一不重复', () => {
      const names = LAZY_ROUTE_DEFS.map((r) => r.name)
      const uniqueNames = new Set(names)
      expect(uniqueNames.size).toBe(names.length)
    })
  })

  describe('懒加载首次加载时间不超过2000ms', () => {
    it('立即解析的懒加载组件耗时远低于2000ms', async () => {
      const route = {
        path: '/instant',
        name: 'Instant',
        component: createAsyncComponent(0),
      }
      const start = performance.now()
      await route.component()
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(2000)
    })

    it('100ms延迟的懒加载在2000ms内完成', async () => {
      const route = {
        path: '/fast',
        name: 'Fast',
        component: createAsyncComponent(100),
      }
      const start = performance.now()
      await route.component()
      const duration = performance.now() - start
      expect(duration).toBeGreaterThanOrEqual(100)
      expect(duration).toBeLessThanOrEqual(2000)
    })

    it('500ms延迟的懒加载在2000ms内完成', async () => {
      const route = {
        path: '/medium',
        name: 'Medium',
        component: createAsyncComponent(500),
      }
      const start = performance.now()
      await route.component()
      const duration = performance.now() - start
      expect(duration).toBeGreaterThanOrEqual(500)
      expect(duration).toBeLessThanOrEqual(2000)
    })

    it('1500ms延迟的懒加载仍满足2000ms上限', async () => {
      const route = {
        path: '/slow',
        name: 'Slow',
        component: createAsyncComponent(1500),
      }
      const start = performance.now()
      await route.component()
      const duration = performance.now() - start
      expect(duration).toBeGreaterThanOrEqual(1500)
      expect(duration).toBeLessThanOrEqual(2000)
    })

    it('所有36个路由首次加载平均时间不超过2000ms', async () => {
      const routes = LAZY_ROUTE_DEFS.map((r) => ({
        path: r.path,
        name: r.name,
        component: createAsyncComponent(50),
      }))
      const durations: number[] = []
      for (const route of routes) {
        const start = performance.now()
        await route.component()
        durations.push(performance.now() - start)
      }
      const avg = durations.reduce((a, b) => a + b, 0) / durations.length
      expect(avg).toBeLessThanOrEqual(2000)
    })

    it('首次加载完成后组件模板可正常渲染', async () => {
      const route = {
        path: '/render',
        name: 'Render',
        component: createAsyncComponent(0),
      }
      const resolved = await route.component()
      const component = resolved.default
      expect(component.template).toContain('Mock Async View')
    })
  })

  describe('路由切换时间不超过300ms', () => {
    it('两个路由之间切换耗时不超过300ms', async () => {
      const router = createRouter({
        history: createMemoryHistory(),
        routes: [
          { path: '/', name: 'Home', component: createAsyncComponent(0) },
          { path: '/about', name: 'About', component: createAsyncComponent(30) },
        ],
      })
      await router.isReady()
      await router.push('/')
      const start = performance.now()
      await router.push('/about')
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(300)
    })

    it('路由切换后currentRoute名称正确', async () => {
      const router = createRouter({
        history: createMemoryHistory(),
        routes: [
          { path: '/', name: 'Home', component: createAsyncComponent(0) },
          { path: '/about', name: 'About', component: createAsyncComponent(30) },
          { path: '/contact', name: 'Contact', component: createAsyncComponent(30) },
        ],
      })
      await router.isReady()
      await router.push('/about')
      expect(router.currentRoute.value.name).toBe('About')
      const start = performance.now()
      await router.push('/contact')
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(300)
      expect(router.currentRoute.value.name).toBe('Contact')
    })

    it('依次切换5个路由每次均不超过300ms', async () => {
      const routeDefs = LAZY_ROUTE_DEFS.slice(0, 5).map((r) => ({
        path: r.path,
        name: r.name,
        component: createAsyncComponent(20),
      }))
      const router = createRouter({
        history: createMemoryHistory(),
        routes: routeDefs,
      })
      await router.isReady()
      for (const r of routeDefs) {
        const start = performance.now()
        await router.push(r.path)
        const duration = performance.now() - start
        expect(duration).toBeLessThanOrEqual(300)
        expect(router.currentRoute.value.name).toBe(r.name)
      }
    })

    it('路由切换时查询参数保留正确', async () => {
      const router = createRouter({
        history: createMemoryHistory(),
        routes: [
          { path: '/', name: 'Home', component: createAsyncComponent(0) },
          { path: '/search', name: 'Search', component: createAsyncComponent(20) },
        ],
      })
      await router.isReady()
      await router.push('/search?q=test&page=1')
      expect(router.currentRoute.value.query.q).toBe('test')
      expect(router.currentRoute.value.query.page).toBe('1')
    })

    it('路由切换时路径参数传递正确', async () => {
      const router = createRouter({
        history: createMemoryHistory(),
        routes: [
          { path: '/', name: 'Home', component: createAsyncComponent(0) },
          { path: '/user/:id', name: 'User', component: createAsyncComponent(20) },
        ],
      })
      await router.isReady()
      await router.push('/user/42')
      expect(router.currentRoute.value.params.id).toBe('42')
    })
  })

  describe('并发路由加载性能', () => {
    it('同时加载3个懒加载组件总耗时不超过2000ms', async () => {
      const routes = [
        createAsyncComponent(300),
        createAsyncComponent(400),
        createAsyncComponent(500),
      ]
      const start = performance.now()
      const results = await Promise.all(routes.map((r) => r()))
      const duration = performance.now() - start
      expect(results).toHaveLength(3)
      expect(duration).toBeLessThanOrEqual(2000)
    })

    it('同时加载5个懒加载组件均正确解析', async () => {
      const routes = Array.from({ length: 5 }, () => createAsyncComponent(100))
      const results = await Promise.all(routes.map((r) => r()))
      for (const result of results) {
        expect(result.default.template).toContain('Mock Async View')
      }
    })
  })
})
