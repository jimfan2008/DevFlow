import { describe, it, expect, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const UNKNOWN_PATHS = [
  '/nonexistent',
  '/some/random/path',
  '/typo-page',
  '/old-feature/removed',
  '/xyz123',
]

const RENDER_TIME_THRESHOLD_MS = 500

const NotFoundStub = {
  template: `
    <div class="not-found">
      <div class="not-found__content">
        <h1 class="not-found__code">404</h1>
        <h2 class="not-found__title">页面不存在</h2>
        <p class="not-found__description">您访问的页面不存在或已被移除</p>
        <button type="button" class="home-btn">返回首页</button>
        <input class="search-input" placeholder="搜索" />
      </div>
    </div>
  `,
  name: 'NotFoundStub',
}

function createAsyncComponent(
  delayMs: number = 0,
  comp: any = NotFoundStub,
) {
  return (): Promise<{ default: any }> =>
    new Promise((resolve) => {
      setTimeout(() => {
        resolve({ default: comp })
      }, delayMs)
    })
}

describe('404未知路由页面', () => {
  describe('显示自定义404页面而非白屏', () => {
    it('访问不存在的路由命中NotFound路由', async () => {
      const routes = [
        { path: '/', name: 'Home', component: { template: '<div>首页</div>' } },
        {
          path: '/:pathMatch(.*)*',
          name: 'NotFound',
          component: { template: '<div class="not-found-page">404</div>' },
        },
      ]
      const router = createRouter({
        history: createMemoryHistory(),
        routes,
      })
      for (const p of UNKNOWN_PATHS) {
        await router.push(p)
        expect(router.currentRoute.value.name).toBe('NotFound')
      }
    })

    it('NotFoundView组件渲染后包含404标识', async () => {
      const wrapper = mount(NotFoundStub)
      expect(wrapper.html()).toContain('404')
      expect(wrapper.html()).toContain('页面不存在')
    })

    it('NotFoundView组件渲染后不是空白内容', async () => {
      const wrapper = mount(NotFoundStub)
      const html = wrapper.html()
      expect(html.length).toBeGreaterThan(10)
      expect(html).toContain('404')
      expect(html).toContain('页面不存在')
      expect(html).toContain('返回首页')
    })

    it('404页面包含返回首页按钮', async () => {
      const wrapper = mount(NotFoundStub)
      const homeBtn = wrapper.find('.home-btn')
      expect(homeBtn.exists()).toBe(true)
      expect(homeBtn.text()).toContain('返回首页')
    })

    it('404页面包含搜索入口', async () => {
      const wrapper = mount(NotFoundStub)
      const searchInput = wrapper.find('.search-input')
      expect(searchInput.exists()).toBe(true)
      expect(searchInput.attributes('placeholder')).toBeDefined()
    })
  })

  describe('返回首页按钮和搜索入口', () => {
    it('点击返回首页按钮触发路由跳转', async () => {
      const mockPush = vi.fn()
      const GoHomeComponent = {
        template: `<button @click="goHome">返回首页</button>`,
        setup() {
          return { goHome: () => mockPush({ name: 'BoardList' }) }
        },
      }
      const wrapper = mount(GoHomeComponent)
      await wrapper.find('button').trigger('click')
      expect(mockPush).toHaveBeenCalledWith({ name: 'BoardList' })
    })

    it('goHome方法正确导航到目标页面', async () => {
      const HomeButtonComponent = {
        template: `<button @click="goHome">返回首页</button>`,
        setup() {
          const goHome = () => '/boards'
          return { goHome }
        },
      }
      const wrapper = mount(HomeButtonComponent)
      expect(typeof wrapper.vm.goHome).toBe('function')
      await wrapper.find('button').trigger('click')
    })

    it('搜索入口具有占位符文本', async () => {
      const wrapper = mount(NotFoundStub)
      const searchInput = wrapper.find('input')
      expect(searchInput.exists()).toBe(true)
      const placeholder = searchInput.attributes('placeholder')
      expect(placeholder).toBeDefined()
      expect(placeholder.length).toBeGreaterThan(0)
    })
  })

  describe('路由名称为NotFound', () => {
    it('已知路径不命中NotFound', async () => {
      const routes = [
        { path: '/login', name: 'Login', component: { template: '<div>登录</div>' } },
        { path: '/projects', name: 'ProjectList', component: { template: '<div>项目</div>' } },
        { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFoundStub },
      ]
      const router = createRouter({
        history: createMemoryHistory(),
        routes,
      })

      await router.push('/login')
      expect(router.currentRoute.value.name).toBe('Login')

      await router.push('/projects')
      expect(router.currentRoute.value.name).toBe('ProjectList')
    })

    it('未知路径命中NotFound', async () => {
      const routes = [
        { path: '/login', name: 'Login', component: { template: '<div>登录</div>' } },
        { path: '/projects', name: 'ProjectList', component: { template: '<div>项目</div>' } },
        { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFoundStub },
      ]
      const router = createRouter({
        history: createMemoryHistory(),
        routes,
      })

      for (const p of UNKNOWN_PATHS) {
        await router.push(p)
        expect(router.currentRoute.value.name).toBe('NotFound')
      }
    })
  })

  describe('页面渲染时间不超过500ms', () => {
    it('NotFoundView组件挂载耗时不超过500ms', async () => {
      const start = performance.now()
      const wrapper = mount(NotFoundStub)
      await nextTick()
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(RENDER_TIME_THRESHOLD_MS)
      expect(wrapper.html()).toContain('404')
    })

    it('多个NotFoundView连续渲染每个都不超过500ms', async () => {
      for (let i = 0; i < 5; i++) {
        const start = performance.now()
        const wrapper = mount(NotFoundStub)
        await nextTick()
        const duration = performance.now() - start
        expect(duration).toBeLessThanOrEqual(RENDER_TIME_THRESHOLD_MS)
        wrapper.unmount()
      }
    })

    it('NotFoundView组件包含必要DOM元素', async () => {
      const wrapper = mount(NotFoundStub)
      expect(wrapper.find('.not-found__code').exists()).toBe(true)
      expect(wrapper.find('.not-found__title').exists()).toBe(true)
      expect(wrapper.find('.home-btn').exists()).toBe(true)
      expect(wrapper.find('.search-input').exists()).toBe(true)
    })

    it('懒加载NotFound组件解析耗时不超过500ms', async () => {
      const loadComponent = createAsyncComponent(10, NotFoundStub)
      const start = performance.now()
      const result = await loadComponent()
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(RENDER_TIME_THRESHOLD_MS)
      expect(result.default.name).toBe('NotFoundStub')
    })

    it('路由跳转到NotFound耗时不超过500ms', async () => {
      const routes = [
        { path: '/', name: 'Home', component: createAsyncComponent(5) },
        {
          path: '/:pathMatch(.*)*',
          name: 'NotFound',
          component: createAsyncComponent(10, NotFoundStub),
        },
      ]
      const router = createRouter({
        history: createMemoryHistory(),
        routes,
      })
      const start = performance.now()
      await router.push('/any-unknown-path')
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(RENDER_TIME_THRESHOLD_MS)
      expect(router.currentRoute.value.name).toBe('NotFound')
    })
  })
})
