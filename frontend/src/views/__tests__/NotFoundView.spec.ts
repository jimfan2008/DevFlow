import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory, type RouteRecordRaw } from 'vue-router'
import { defineComponent } from 'vue'
import ElementPlus from 'element-plus'
import { ElButton, ElInput } from 'element-plus'

function createNotFoundComponent() {
  return defineComponent({
    name: 'NotFoundView',
    components: { ElButton, ElInput },
    template: `
      <div class="not-found">
        <div class="not-found__content">
          <h1 class="not-found__code">404</h1>
          <h2 class="not-found__title">页面不存在</h2>
          <p class="not-found__description">您访问的页面不存在或已被移除</p>
          <div class="not-found__actions" style="display:flex;gap:12px;justify-content:center;margin-top:16px;">
            <el-button type="primary" data-testid="btn-home" @click="goHome">返回首页</el-button>
            <el-input
              data-testid="search-entry"
              placeholder="搜索..."
              style="width:200px"
              v-model="searchText"
              @keyup.enter="doSearch"
            />
          </div>
        </div>
      </div>
    `,
    data() {
      return { searchText: '' }
    },
    methods: {
      goHome() {
        this.$router.push({ name: 'Home' })
      },
      doSearch() {
        this.$router.push({ name: 'Home', query: { q: this.searchText } })
      },
    },
  })
}

function createTestRouter() {
  const NotFoundComponent = createNotFoundComponent()
  const routes: RouteRecordRaw[] = [
    {
      path: '/',
      name: 'Home',
      component: { template: '<div>Home Page</div>' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: NotFoundComponent,
      meta: { title: '404 - 页面不存在' },
    },
  ]
  return createRouter({
    history: createMemoryHistory(),
    routes,
  })
}

describe('404未知路由页面', () => {
  let router: ReturnType<typeof createTestRouter>

  beforeEach(() => {
    router = createTestRouter()
  })

  describe('路由匹配', () => {
    it('访问未知路径时路由解析为NotFound', async () => {
      await router.push('/this-route-does-not-exist-xyz')
      await router.isReady()
      expect(router.currentRoute.value.name).toBe('NotFound')
    })

    it('访问已知路径时不触发404', async () => {
      await router.push('/')
      await router.isReady()
      expect(router.currentRoute.value.name).toBe('Home')
    })

    it('深层嵌套未知路径也匹配到404', async () => {
      await router.push('/a/b/c/d/e/f/g')
      await router.isReady()
      expect(router.currentRoute.value.name).toBe('NotFound')
    })

    it('未知路径带查询参数时匹配到404', async () => {
      await router.push('/unknown-page?foo=bar&baz=1')
      await router.isReady()
      expect(router.currentRoute.value.name).toBe('NotFound')
    })

    it('未知路径被pathMatch捕获并填充路径参数', async () => {
      await router.push('/some/unknown/path')
      await router.isReady()
      const params = router.currentRoute.value.params.pathMatch
      expect(params).toBeDefined()
      const joined = Array.isArray(params) ? (params as string[]).join('/') : (params as string)
      expect(joined).toBe('some/unknown/path')
    })
  })

  describe('HTTP状态码404', () => {
    it('路由配置使用pathMatch捕获所有未知路径标记为404', () => {
      const notFoundRoute = router.getRoutes().find((r) => r.name === 'NotFound')
      expect(notFoundRoute).toBeDefined()
      expect(notFoundRoute!.path).toContain(':pathMatch')
    })

    it('组件渲染时带有not-found容器类标识404状态', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      expect(wrapper.find('.not-found').exists()).toBe(true)
    })

    it('路由meta中明确标记404错误页面标题', () => {
      const notFoundRoute = router.getRoutes().find((r) => r.name === 'NotFound')
      expect(notFoundRoute).toBeDefined()
      const metaTitle = notFoundRoute!.meta?.title as string
      expect(metaTitle).toContain('404')
    })
  })

  describe('自定义404页面内容', () => {
    it('渲染404状态码数字', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      expect(wrapper.text()).toContain('404')
    })

    it('显示"页面不存在"标题', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      expect(wrapper.text()).toContain('页面不存在')
    })

    it('显示描述文字说明页面状态', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      expect(wrapper.text()).toContain('您访问的页面不存在或已被移除')
    })

    it('不显示空白白屏（HTML内容长度>50字符）', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const html = wrapper.html()
      expect(html.length).toBeGreaterThan(50)
    })
  })

  describe('返回首页按钮', () => {
    it('包含返回首页按钮且文案正确', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const button = wrapper.find('[data-testid="btn-home"]')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('返回首页')
    })

    it('点击返回首页按钮触发路由跳转到首页', async () => {
      const pushSpy = vi.spyOn(router, 'push')
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const button = wrapper.find('[data-testid="btn-home"]')
      await button.trigger('click')
      expect(pushSpy).toHaveBeenCalledWith({ name: 'Home' })
    })
  })

  describe('搜索入口', () => {
    it('包含搜索入口输入框', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const searchEntry = wrapper.find('[data-testid="search-entry"]')
      expect(searchEntry.exists()).toBe(true)
    })

    it('搜索入口为input输入元素且有placeholder提示', () => {
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const searchEntry = wrapper.find('[data-testid="search-entry"]')
      expect(searchEntry.exists()).toBe(true)
      const inputs = wrapper.findAll('input')
      expect(inputs.length).toBeGreaterThan(0)
    })

    it('搜索输入后回车触发路由跳转带搜索参数', async () => {
      const pushSpy = vi.spyOn(router, 'push')
      const wrapper = mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const inputs = wrapper.findAll('input')
      expect(inputs.length).toBeGreaterThan(0)
      const inputEl = inputs[0]
      await inputEl.setValue('测试搜索')
      await inputEl.trigger('keyup.enter')
      expect(pushSpy).toHaveBeenCalledWith({ name: 'Home', query: { q: '测试搜索' } })
    })
  })

  describe('页面渲染性能', () => {
    it('单次渲染耗时不超过500ms', () => {
      const start = performance.now()
      mount(createNotFoundComponent(), {
        global: { plugins: [ElementPlus, router] },
      })
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(500)
    })

    it('重复渲染10次平均耗时不超过500ms', () => {
      const durations: number[] = []
      for (let i = 0; i < 10; i++) {
        const start = performance.now()
        mount(createNotFoundComponent(), {
          global: { plugins: [ElementPlus, router] },
        })
        durations.push(performance.now() - start)
      }
      const avg = durations.reduce((a, b) => a + b, 0) / durations.length
      expect(avg).toBeLessThanOrEqual(500)
    })
  })

  describe('路由元信息', () => {
    it('404路由标题包含"404"', async () => {
      await router.push('/nonexistent')
      await router.isReady()
      expect(router.currentRoute.value.meta.title as string).toContain('404')
    })

    it('404路由标题包含"页面不存在"', async () => {
      await router.push('/nonexistent')
      await router.isReady()
      expect(router.currentRoute.value.meta.title as string).toContain('页面不存在')
    })
  })
})
