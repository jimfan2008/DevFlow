import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import WorkflowProgressBar from '@/components/WorkflowProgressBar.vue'

type StepStatus = 'pending' | 'in_progress' | 'qa_review' | 'completed' | 'rejected'

const STATUS_LABELS: Record<StepStatus, string> = {
  pending: '待执行',
  in_progress: '执行中',
  qa_review: '检验中',
  completed: '通过',
  rejected: '未通过',
}

const STEP_NAMES: string[] = [
  '人类用户创建项目',
  '海梅确认核心目标与搭建组织架构',
  '后兴需求分析',
  '后旺架构设计',
  '后富建立开发环境',
  '海梅制订TDD测试用例计划',
  '后发蜂群编写TDD测试用例',
  '海梅制订代码编写计划',
  '后发蜂群编写功能代码',
  '后富部署到测试环境',
  '后达蜂群全面测试',
  '后华安全审计',
  '后富部署到生产环境',
  '后贵完善项目文档',
  '海梅报告交付成果',
  '用户满意度确认与迭代',
]

const STEP_EXECUTORS: string[] = [
  '用户', '海梅(HaiMei)', '后兴(HouXing)', '后旺(HouWang)',
  '后富(HouFu)', '海梅(HaiMei)', '后发(HouFa)', '海梅(HaiMei)',
  '后发(HouFa)', '后富(HouFu)', '后达(HouDa)', '后华(HouHua)',
  '后富(HouFu)', '后贵(HouGui)', '海梅(HaiMei)', '用户',
]

function createStepsData(completedCount: number): Array<{ status: StepStatus }> {
  const steps: Array<{ status: StepStatus }> = []
  for (let i = 0; i < 16; i++) {
    if (i < completedCount) {
      steps.push({ status: 'completed' })
    } else {
      steps.push({ status: 'pending' })
    }
  }
  return steps
}

function computeProgress(steps: Array<{ status: StepStatus }>): number {
  const completed = steps.filter(s => s.status === 'completed').length
  return Math.round((completed / 16) * 100)
}

describe('16步流程进度条组件', () => {
  describe('渲染16个步骤节点', () => {
    it('全部待执行时渲染16个节点', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: createStepsData(0) },
      })
      const nodes = wrapper.findAll('.step-node')
      expect(nodes).toHaveLength(16)
    })

    it('全部完成时渲染16个节点', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: createStepsData(16) },
      })
      const nodes = wrapper.findAll('.step-node')
      expect(nodes).toHaveLength(16)
    })

    it('部分完成时渲染16个节点', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: createStepsData(7) },
      })
      const nodes = wrapper.findAll('.step-node')
      expect(nodes).toHaveLength(16)
    })

    it('每个节点显示步骤编号1-16', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: createStepsData(0) },
      })
      const numbers = wrapper.findAll('.step-number')
      expect(numbers).toHaveLength(16)
      numbers.forEach((el, i) => {
        expect(el.text()).toBe(String(i + 1))
      })
    })

    it('每个节点显示步骤名称', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: createStepsData(0) },
      })
      const names = wrapper.findAll('.step-name')
      names.forEach((el, i) => {
        expect(el.text()).toBe(STEP_NAMES[i])
      })
    })

    it('每个节点显示执行者名称', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: createStepsData(0) },
      })
      const executors = wrapper.findAll('.step-executor')
      executors.forEach((el, i) => {
        expect(el.text()).toBe(STEP_EXECUTORS[i])
      })
    })
  })

  describe('节点状态标签', () => {
    it('待执行状态显示"待执行"', () => {
      const steps = createStepsData(0)
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const labels = wrapper.findAll('.step-status-label')
      for (let i = 0; i < 16; i++) {
        expect(labels[i].text()).toBe('待执行')
      }
    })

    it('执行中状态显示"执行中"', () => {
      const steps: Array<{ status: StepStatus }> = Array(16).fill({ status: 'pending' })
      steps[0] = { status: 'in_progress' }
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const labels = wrapper.findAll('.step-status-label')
      expect(labels[0].text()).toBe('执行中')
    })

    it('检验中状态显示"检验中"', () => {
      const steps: Array<{ status: StepStatus }> = Array(16).fill({ status: 'pending' })
      steps[2] = { status: 'qa_review' }
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const labels = wrapper.findAll('.step-status-label')
      expect(labels[2].text()).toBe('检验中')
    })

    it('通过状态显示"通过"', () => {
      const steps: Array<{ status: StepStatus }> = Array(16).fill({ status: 'pending' })
      steps[0] = { status: 'completed' }
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const labels = wrapper.findAll('.step-status-label')
      expect(labels[0].text()).toBe('通过')
    })

    it('未通过状态显示"未通过"', () => {
      const steps: Array<{ status: StepStatus }> = Array(16).fill({ status: 'pending' })
      steps[5] = { status: 'rejected' }
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const labels = wrapper.findAll('.step-status-label')
      expect(labels[5].text()).toBe('未通过')
    })

    it('混合状态各自显示正确标签', () => {
      const steps: Array<{ status: StepStatus }> = [
        { status: 'completed' },
        { status: 'in_progress' },
        { status: 'qa_review' },
        { status: 'rejected' },
        { status: 'pending' },
        ...Array(11).fill({ status: 'pending' }),
      ]
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const labels = wrapper.findAll('.step-status-label')
      expect(labels[0].text()).toBe('通过')
      expect(labels[1].text()).toBe('执行中')
      expect(labels[2].text()).toBe('检验中')
      expect(labels[3].text()).toBe('未通过')
      expect(labels[4].text()).toBe('待执行')
    })
  })

  describe('进度百分比计算', () => {
    it('0个步骤完成时进度为0%', () => {
      const steps = createStepsData(0)
      const expected = computeProgress(steps)
      expect(expected).toBe(0)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('0%')
    })

    it('4个步骤完成时进度为25%', () => {
      const steps = createStepsData(4)
      const expected = computeProgress(steps)
      expect(expected).toBe(25)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('25%')
    })

    it('8个步骤完成时进度为50%', () => {
      const steps = createStepsData(8)
      const expected = computeProgress(steps)
      expect(expected).toBe(50)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('50%')
    })

    it('12个步骤完成时进度为75%', () => {
      const steps = createStepsData(12)
      const expected = computeProgress(steps)
      expect(expected).toBe(75)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('75%')
    })

    it('16个步骤全部完成时进度为100%', () => {
      const steps = createStepsData(16)
      const expected = computeProgress(steps)
      expect(expected).toBe(100)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('100%')
    })

    it('已完成步骤不计入in_progress/qa_review/rejected', () => {
      const steps: Array<{ status: StepStatus }> = [
        { status: 'completed' },
        { status: 'completed' },
        { status: 'completed' },
        { status: 'in_progress' },
        { status: 'qa_review' },
        { status: 'rejected' },
        ...Array(10).fill({ status: 'pending' }),
      ]
      const expected = computeProgress(steps)
      expect(expected).toBe(18)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('18%')
    })

    it('进度百分比取整到整数', () => {
      const steps: Array<{ status: StepStatus }> = [
        { status: 'completed' },
        ...Array(15).fill({ status: 'pending' }),
      ]
      const expected = computeProgress(steps)
      expect(expected).toBe(6)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('6%')
    })
  })

  describe('进度条视觉元素', () => {
    it('使用el-progress显示进度百分比', () => {
      const steps = createStepsData(8)
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const progress = wrapper.findComponent({ name: 'ElProgress' })
      expect(progress.exists()).toBe(true)
    })

    it('el-progress的percentage属性值等于计算结果', () => {
      const steps = createStepsData(10)
      const expected = computeProgress(steps)
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      const progress = wrapper.findComponent({ name: 'ElProgress' })
      expect(progress.props('percentage')).toBe(expected)
    })
  })

  describe('边界情况', () => {
    it('steps为空数组时进度为0%', () => {
      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps: [] },
      })
      const nodes = wrapper.findAll('.step-node')
      expect(nodes).toHaveLength(0)
      expect(wrapper.text()).toContain('0%')
    })

    it('所有步骤为rejected时进度为0%', () => {
      const steps: Array<{ status: StepStatus }> = Array(16).fill({ status: 'rejected' })
      const expected = computeProgress(steps)
      expect(expected).toBe(0)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('0%')
    })

    it('所有步骤为in_progress时进度为0%', () => {
      const steps: Array<{ status: StepStatus }> = Array(16).fill({ status: 'in_progress' })
      const expected = computeProgress(steps)
      expect(expected).toBe(0)

      const wrapper = mount(WorkflowProgressBar, {
        global: { plugins: [ElementPlus] },
        props: { steps },
      })
      expect(wrapper.text()).toContain('0%')
    })
  })
})
