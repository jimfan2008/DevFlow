import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import TabletLayout from '@/components/layout/TabletLayout.vue'

function setViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  })
  window.dispatchEvent(new Event('resize'))
}

describe('响应式平板端布局', () => {
  beforeEach(() => {
    setViewport(1024)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('平板端双栏布局', () => {
    it('在平板宽度(768-1199px)下渲染双栏容器', () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.tablet-layout').exists()).toBe(true)
      expect(wrapper.findAll('.tablet-layout__column')).toHaveLength(2)
    })

    it('左侧栏为侧边导航栏', () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const columns = wrapper.findAll('.tablet-layout__column')
      expect(columns[0].classes()).toContain('tablet-layout__sidebar')
    })

    it('右侧栏为核心内容区', () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const columns = wrapper.findAll('.tablet-layout__column')
      expect(columns[1].classes()).toContain('tablet-layout__content')
    })

    it('在桌面宽度(≥1200px)下三栏布局不应用平板样式', () => {
      setViewport(1440)
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.tablet-layout').exists()).toBe(true)
    })
  })

  describe('侧边栏折叠/展开', () => {
    it('初始状态侧边栏展开', () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      expect(wrapper.find('.tablet-layout__sidebar').classes()).not.toContain('collapsed')
    })

    it('点击折叠按钮后侧边栏折叠', async () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.tablet-layout__toggle')
      await toggleBtn.trigger('click')
      expect(wrapper.find('.tablet-layout__sidebar').classes()).toContain('collapsed')
    })

    it('再次点击折叠按钮侧边栏展开', async () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.tablet-layout__toggle')
      await toggleBtn.trigger('click')
      await toggleBtn.trigger('click')
      expect(wrapper.find('.tablet-layout__sidebar').classes()).not.toContain('collapsed')
    })
  })

  describe('折叠动画响应时间', () => {
    it('侧边栏折叠动画时间≤300ms', () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const sidebar = wrapper.find('.tablet-layout__sidebar')
      const transitionDuration = parseFloat(
        getComputedStyle(sidebar.element).transitionDuration || '0'
      ) * 1000
      expect(transitionDuration).toBeLessThanOrEqual(300)
    })

    it('侧边栏展开动画时间≤300ms', async () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.tablet-layout__toggle')
      await toggleBtn.trigger('click')
      const sidebar = wrapper.find('.tablet-layout__sidebar')
      const transitionDuration = parseFloat(
        getComputedStyle(sidebar.element).transitionDuration || '0'
      ) * 1000
      expect(transitionDuration).toBeLessThanOrEqual(300)
    })
  })

  describe('核心内容区域自适应', () => {
    it('侧边栏展开时内容区占剩余宽度', () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const content = wrapper.find('.tablet-layout__content')
      expect(getComputedStyle(content.element).flex).toBe('1')
    })

    it('侧边栏折叠后内容区宽度自动扩展', async () => {
      const wrapper = mount(TabletLayout, {
        global: { plugins: [ElementPlus] },
      })
      const toggleBtn = wrapper.find('.tablet-layout__toggle')
      await toggleBtn.trigger('click')
      const content = wrapper.find('.tablet-layout__content')
      expect(getComputedStyle(content.element).flex).toBe('1')
    })
  })
})
