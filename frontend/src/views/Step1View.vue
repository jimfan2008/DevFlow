<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { workflowApi } from '@/api/modules/workflow'
import { ArrowLeft } from '@element-plus/icons-vue'

const props = defineProps<{ projectId: string }>()
const router = useRouter()

const projectName = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    projectName.value = data?.name || ''
  } catch {} finally {
    loading.value = false
  }
})

function goNext() {
  router.push({ name: 'Step2', params: { projectId: props.projectId }, query: { name: projectName.value } })
}

function goBack() {
  router.push({ name: 'ProjectDetail', params: { projectId: props.projectId } })
}
</script>

<template>
<div class="step1-view" v-loading="loading">
  <div class="step1-view__header">
    <div class="step1-view__header-left">
      <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
      <div>
        <h1>第一步：项目概览</h1>
        <p class="step1-view__subtitle">{{ projectName }}</p>
      </div>
    </div>
  </div>

  <div class="step1-view__card">
    <div class="step1-view__card-icon">🚀</div>
    <h2>欢迎来到 DevFlow 工作流</h2>
    <p class="step1-view__desc">
      本工作流将依次完成以下步骤，引导项目从需求到交付的全生命周期管理：
    </p>
    <ul class="step1-view__steps">
      <li><strong>步骤2</strong>：确认核心目标与搭建组织架构 — 海梅主动对话明确项目目标与团队</li>
      <li><strong>步骤3</strong>：需求分析 — 由后兴驱动的完整需求分析与用户故事</li>
      <li><strong>步骤4</strong>：架构设计 — 由后旺驱动的技术架构与系统设计</li>
      <li><strong>步骤5</strong>：建立开发环境 — 后富自动初始化项目并配置环境</li>
      <li><strong>步骤6</strong>：制订TDD测试用例计划 — 海梅驱动多轮迭代生成测试计划</li>
      <li><strong>步骤7</strong>：编写TDD测试用例 — 测试用例生成与校验</li>
      <li><strong>步骤8</strong>：制订代码编写计划 — 代码实现规划</li>
      <li><strong>步骤9</strong>：编写功能代码 — 功能代码自动生成</li>
      <li><strong>步骤10</strong>：部署到测试环境 — 自动化部署</li>
      <li><strong>步骤11</strong>：全面测试 — 自动化测试执行</li>
      <li><strong>步骤12</strong>：安全审计 — 安全扫描与合规检查</li>
      <li><strong>步骤13</strong>：部署到生产环境 — 生产发布</li>
      <li><strong>步骤14</strong>：完善项目文档 — 文档自动生成</li>
      <li><strong>步骤15</strong>：报告交付成果 — 交付报告编制</li>
      <li><strong>步骤16</strong>：用户满意度确认与迭代 — 反馈收集与后续规划</li>
    </ul>
    <div class="step1-view__action-row">
      <el-button type="primary" size="large" @click="goNext">
        开始工作流 →
      </el-button>
    </div>
  </div>
</div>
</template>

<style scoped lang="scss">
.step1-view {
  max-width: 800px; margin: 0 auto; padding: 32px 24px;

  &__header {
    margin-bottom: 32px;
    &-left { display: flex; align-items: flex-start; gap: 16px; h1 { margin: 0; font-size: 24px; font-weight: 600; } }
  }
  &__subtitle { margin: 4px 0 0; color: #909399; font-size: 14px; }

  &__card {
    text-align: center; padding: 40px 32px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px;
  }
  &__card-icon { font-size: 48px; line-height: 1; }
  &__desc { font-size: 14px; color: #606266; margin: 16px 0; line-height: 1.6; }
  &__steps {
    text-align: left; list-style: none; padding: 0; margin: 24px 0;
    li {
      padding: 6px 0; font-size: 13px; color: #606266; border-bottom: 1px solid #f0f0f0;
      &:last-child { border-bottom: none; }
    }
  }
  &__action-row { margin-top: 24px; }
}
</style>
