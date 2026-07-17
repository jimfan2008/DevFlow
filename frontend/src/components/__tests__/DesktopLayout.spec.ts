import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import DesktopLayout from '@/components/layout/DesktopLayout.vue'

function setViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
  window.dispatchEvent(new Event('resize'))
}

describe('响应式桌面端布局', () => {
  beforeEach(() => {
    setViewport(1440)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('桌面端三栏布局结构', () => {
    it('在桌面宽度(≥1280px)下渲染三栏容器', () => {
      setViewport(1280)
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout').exists()).toBe(true)
      expect(wrapper.findAll('.desktop-layout__column')).toHaveLength(3)
    })

    it('第一栏为侧边导航栏', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const columns = wrapper.findAll('.desktop-layout__column')
      expect(columns[0].classes()).toContain('desktop-layout__sidebar')
    })

    it('第二栏为核心内容区', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const columns = wrapper.findAll('.desktop-layout__column')
      expect(columns[1].classes()).toContain('desktop-layout__content')
    })

    it('第三栏为详情面板', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const columns = wrapper.findAll('.desktop-layout__column')
      expect(columns[2].classes()).toContain('desktop-layout__detail')
    })

    it('在非桌面宽度(1024px)下不渲染三栏布局', () => {
      setViewport(1024)
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout').exists()).toBe(false)
    })
  })

  describe('首屏加载性能', () => {
    it('首次渲染耗时不超过2000ms', () => {
      const start = performance.now()
      mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const duration = performance.now() - start
      expect(duration).toBeLessThanOrEqual(2000)
    })

    it('连续渲染5次平均耗时不超过2000ms', () => {
      const durations: number[] = []
      for (let i = 0; i < 5; i++) {
        const start = performance.now()
        mount(DesktopLayout, {
          global: { plugins: [ElementPlus] },
        })
        durations.push(performance.now() - start)
      }
      const avg = durations.reduce((a, b) => a + b, 0) / durations.length
      expect(avg).toBeLessThanOrEqual(2000)
    })
  })

  describe('交互元素显示', () => {
    it('侧边栏显示折叠/展开按钮', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.desktop-layout__toggle')
      expect(toggleBtn.exists()).toBe(true)
    })

    it('核心内容区显示页面标题', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const content = wrapper.find('.desktop-layout__content')
      expect(content.find('.desktop-layout__page-title').exists()).toBe(true)
    })

    it('详情面板显示关闭按钮', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const detail = wrapper.find('.desktop-layout__detail')
      expect(detail.find('.desktop-layout__close-btn').exists()).toBe(true)
    })

    it('侧边栏菜单项可点击', async () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const menuItems = wrapper.findAll('.desktop-layout__menu-item')
      expect(menuItems.length).toBeGreaterThan(0)
      await menuItems[0].trigger('click')
      expect(menuItems[0].classes()).toContain('active')
    })

    it('详情面板可通过关闭按钮隐藏', async () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const closeBtn = wrapper.find('.desktop-layout__close-btn')
      await closeBtn.trigger('click')
      expect(wrapper.find('.desktop-layout__detail').isVisible()).toBe(false)
    })
  })

  describe('侧边栏折叠功能', () => {
    it('初始状态侧边栏展开', () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout__sidebar').classes()).not.toContain('collapsed')
    })

    it('点击折叠按钮后侧边栏折叠', async () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.desktop-layout__toggle')
      await toggleBtn.trigger('click')
      expect(wrapper.find('.desktop-layout__sidebar').classes()).toContain('collapsed')
    })

    it('侧边栏折叠后内容区宽度自适应', async () => {
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.desktop-layout__toggle')
      await toggleBtn.trigger('click')
      const content = wrapper.find('.desktop-layout__content')
      expect(getComputedStyle(content.element).flex).toBe('1 1 0%')
    })
  })

  describe('布局响应式边界', () => {
    it('宽度1280px时精确触发桌面布局', () => {
      setViewport(1280)
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout').exists()).toBe(true)
      expect(wrapper.findAll('.desktop-layout__column')).toHaveLength(3)
    })

    it('宽度1279px时不触发桌面布局', () => {
      setViewport(1279)
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout').exists()).toBe(false)
    })

    it('窗口从窄变宽时切换到三栏布局', async () => {
      setViewport(1024)
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout').exists()).toBe(false)
      setViewport(1440)
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.desktop-layout').exists()).toBe(true)
      expect(wrapper.findAll('.desktop-layout__column')).toHaveLength(3)
    })

    it('窗口从宽变窄时退出三栏布局', async () => {
      setViewport(1440)
      const wrapper = mount(DesktopLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.desktop-layout').exists()).toBe(true)
      setViewport(1024)
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.desktop-layout').exists()).toBe(false)
    })
  })
})
