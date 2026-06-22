<template>
  <div class="project-detail-view" v-loading="loading">
    <div class="project-detail-view__header">
      <el-button :icon="ArrowLeft" text @click="router.push({ name: 'ProjectList' })">返回</el-button>
      <h2>{{ store.currentProject?.name }}</h2>
      <el-tag v-if="store.currentProject" :type="statusTagType(store.currentProject.status)">{{ statusLabel(store.currentProject.status) }}</el-tag>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="流程步骤" name="workflow">
        <div class="project-detail-view__workflow">
          <h3>16步自动化开发流程</h3>
          <p class="project-detail-view__workflow-sub">DevFlow 全自动 AI Agent 驱动开发流水线</p>
          <div class="project-detail-view__workflow-steps">
            <div
              v-for="(step, i) in workflowSteps"
              :key="i"
              class="project-detail-view__workflow-step"
              :class="{
                'project-detail-view__workflow-step--active': workflowStatus && (workflowStatus.steps?.[String(i + 1)]?.status === 'in_progress' || workflowStatus.steps?.[String(i + 1)]?.status === 'qa_review'),
                'project-detail-view__workflow-step--completed': workflowStatus?.steps?.[String(i + 1)]?.status === 'completed',
              }"
              @click="goToStep(i + 1)"
            >
              <div class="project-detail-view__workflow-step-num">{{ i + 1 }}</div>
              <div class="project-detail-view__workflow-step-info">
                <div class="project-detail-view__workflow-step-name">{{ step.name }}</div>
                <div class="project-detail-view__workflow-step-executor">{{ step.executor }}</div>
              </div>
              <div class="project-detail-view__workflow-step-action" @click.stop>
                <el-button
                  v-if="workflowStatus?.steps?.[String(i + 1)]?.status === 'completed'"
                  size="small"
                  type="success"
                  plain
                  disabled
                >
                  ✓ 已完成
                </el-button>
                <el-button
                  v-else-if="workflowStatus?.steps?.[String(i + 1)]?.status === 'in_progress'"
                  size="small"
                  type="primary"
                  @click="goToStep(i + 1)"
                >
                  进行中
                </el-button>
                <el-button
                  v-else-if="workflowStatus?.steps?.[String(i + 1)]?.status === 'qa_review'"
                  size="small"
                  type="warning"
                  @click="goToStep(i + 1)"
                >
                  待检验
                </el-button>
                <el-button
                  v-else-if="workflowStatus?.steps?.[String(i + 1)]?.status === 'rejected'"
                  size="small"
                  type="danger"
                  @click="goToStep(i + 1)"
                >
                  已退回
                </el-button>
                <el-button
                  v-else-if="isNextStep(i + 1)"
                  size="small"
                  type="primary"
                  @click="goToStep(i + 1)"
                >
                  开始执行
                </el-button>
                <el-button
                  v-else
                  size="small"
                  type="primary"
                  plain
                  @click="goToStep(i + 1)"
                >
                  查看/执行
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="关联需求" name="requirement">
        <el-button @click="router.push({ name: 'Requirements' })" type="primary" plain>前往需求管理</el-button>
      </el-tab-pane>

      <el-tab-pane label="任务统计" name="tasks">
        <el-table :data="tasks" stripe v-if="tasks.length">
          <el-table-column prop="title" label="任务标题" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="priority" label="优先级" width="100" />
        </el-table>
        <el-empty v-else description="暂无任务" />
      </el-tab-pane>

      <el-tab-pane label="通知列表" name="notifications">
        <el-table :data="projectNotifications" stripe v-if="projectNotifications.length">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无通知" />
      </el-tab-pane>

      <el-tab-pane label="基本信息" name="info">
        <el-descriptions :column="2" border v-if="store.currentProject">
          <el-descriptions-item label="项目名称">{{ store.currentProject.name }}</el-descriptions-item>
          <el-descriptions-item label="Slug">{{ store.currentProject.slug }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabel(store.currentProject.status) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(store.currentProject.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ store.currentProject.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="仓库地址" :span="2">
            <el-link v-if="store.currentProject.repo_url" :href="store.currentProject.repo_url" target="_blank" type="primary">{{ store.currentProject.repo_url }}</el-link>
            <span v-else>-</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/useProjectStore'

const router = useRouter()
const route = useRoute()
const store = useProjectStore()
const activeTab = ref('workflow')
const tasks = ref<any[]>([])
const projectNotifications = ref<any[]>([])
const loading = ref(false)
const workflowStatus = ref<Record<string, any> | null>(null)

const workflowSteps = [
  { name: '人类用户创建项目', executor: '用户' },
  { name: '海梅确认核心目标与搭建组织架构', executor: '海梅(HaiMei)' },
  { name: '后兴需求分析', executor: '后兴(HouXing)' },
  { name: '后旺架构设计', executor: '后旺(HouWang)' },
  { name: '后富建立开发环境', executor: '后富(HouFu)' },
  { name: '海梅制订TDD测试用例计划', executor: '海梅(HaiMei)' },
  { name: '后发蜂群编写TDD测试用例', executor: '后发(HouFa)' },
  { name: '海梅制订代码编写计划', executor: '海梅(HaiMei)' },
  { name: '后发蜂群编写功能代码', executor: '后发(HouFa)' },
  { name: '后富部署到测试环境', executor: '后富(HouFu)' },
  { name: '后达蜂群全面测试', executor: '后达(HouDa)' },
  { name: '后华安全审计', executor: '后华(HouHua)' },
  { name: '后富部署到生产环境', executor: '后富(HouFu)' },
  { name: '后贵完善项目文档', executor: '后贵(HouGui)' },
  { name: '海梅报告交付成果', executor: '海梅(HaiMei)' },
  { name: '用户满意度确认与迭代', executor: '用户' },
]

function isNextStep(stepNum: number): boolean {
  if (!workflowStatus.value) return stepNum === 1
  if (stepNum === 1) return true
  const prevStatus = workflowStatus.value.steps?.[String(stepNum - 1)]?.status
  const currentStatus = workflowStatus.value.steps?.[String(stepNum)]?.status
  return currentStatus === 'pending' && prevStatus === 'completed'
}

function goToStep(stepNum: number) {
  const projectId = route.params.projectId as string
  const projectName = store.currentProject?.name || ''
  if (stepNum === 2) {
    router.push({ name: 'Step2', params: { projectId }, query: { name: projectName } })
  } else if (stepNum === 3) {
    router.push({ name: 'Step3', params: { projectId }, query: { name: projectName } })
  } else if (stepNum === 4) {
    router.push({ name: 'Step4', params: { projectId }, query: { name: projectName } })
  } else {
    router.push({ name: 'WorkflowStep', params: { projectId, stepNumber: stepNum }, query: { name: projectName } })
  }
}

onMounted(async () => {
  const projectId = route.params.projectId as string
  loading.value = true
  try {
    await store.fetchProjectDetail(projectId)
    const [taskRes, notifRes, statusRes] = await Promise.all([
      store.fetchProjectTasks(projectId),
      store.fetchProjectNotifications(projectId),
      import('@/api/modules/workflow').then(m => m.workflowApi.getStatus(projectId)),
    ])
    tasks.value = taskRes || []
    projectNotifications.value = notifRes?.notifications || []
    workflowStatus.value = (statusRes as any)?.data || null
  } finally {
    loading.value = false
  }
})

function statusLabel(status: string) {
  const map: Record<string, string> = { draft: '草稿', active: '进行中', completed: '已完成', archived: '已归档' }
  return map[status] || status
}

function statusTagType(status: string) {
  const map: Record<string, string> = { draft: 'info', active: '', completed: 'success', archived: 'warning' }
  return (map[status] || 'info') as any
}

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.project-detail-view {
  &__header {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    margin-bottom: $spacing-6;
    h2 {
      margin: 0;
      font-family: $font-display;
      font-size: $display-lg-size;
      font-weight: $display-lg-weight;
      line-height: $display-lg-leading;
      letter-spacing: $display-lg-tracking;
      color: $ink;
    }
  }

  &__workflow {
    h3 {
      margin: 0 0 $spacing-xxs;
      font-family: $font-display;
      font-size: $tagline-size;
    }
  }

  &__workflow-sub {
    color: $ink-muted-48;
    margin: 0 0 $spacing-4;
    font-size: $caption-size;
  }

  &__workflow-steps {
    display: flex;
    flex-direction: column;
    gap: $spacing-xs;
  }

  &__workflow-step {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-4;
    background: $canvas;
    border: 1px solid $hairline;
    border-radius: $radius-sm;
    transition: all 0.2s;
    cursor: pointer;

    &:hover {
      border-color: $primary;
      background: rgba($primary, 0.03);
    }

    &--active {
      border-color: $primary;
      background: rgba($primary, 0.03);
    }

    &--completed {
      border-color: $status-done;
      background: rgba($status-done, 0.03);
      .project-detail-view__workflow-step-num {
        background: $status-done;
        color: $on-primary;
      }
      .project-detail-view__workflow-step-name {
        color: $ink-muted-48;
      }
    }

    &-num {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: $canvas-parchment;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: $fine-print-size;
      font-weight: 600;
      color: $ink-muted-48;
      flex-shrink: 0;
    }

    &-info {
      flex: 1;
      min-width: 0;
    }

    &-name {
      font-size: $body-size;
      font-weight: 500;
      color: $ink;
    }

    &-executor {
      font-size: $fine-print-size;
      color: $ink-muted-48;
    }

    &-action {
      flex-shrink: 0;
    }
  }
}
</style>
