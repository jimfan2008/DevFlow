<template>
  <div class="haimei-panel" v-loading="loading">
    <div class="haimei-panel__header">
      <div class="haimei-panel__title-row">
        <span class="haimei-panel__icon">👩‍💼</span>
        <h3 class="haimei-panel__title">海梅工作流监控</h3>
        <el-tag v-if="summary" :type="summary.progress_pct >= 100 ? 'success' : 'warning'" size="small">
          {{ summary.progress_pct }}%
        </el-tag>
      </div>
      <div class="haimei-panel__actions">
        <el-button size="small" text @click="refreshData" :icon="Refresh" :loading="loading" />
      </div>
    </div>

    <div v-if="haimeiMessage" class="haimei-panel__message">
      {{ haimeiMessage }}
    </div>

    <div v-if="summary" class="haimei-panel__summary">
      <div class="haimei-panel__stat">
        <span class="haimei-panel__stat-value">{{ summary.completed }}</span>
        <span class="haimei-panel__stat-label">已完成</span>
      </div>
      <div class="haimei-panel__stat">
        <span class="haimei-panel__stat-value haimei-panel__stat-value--active">{{ summary.in_progress }}</span>
        <span class="haimei-panel__stat-label">进行中</span>
      </div>
      <div class="haimei-panel__stat">
        <span class="haimei-panel__stat-value haimei-panel__stat-value--review">{{ summary.qa_review }}</span>
        <span class="haimei-panel__stat-label">待检验</span>
      </div>
      <div class="haimei-panel__stat">
        <span class="haimei-panel__stat-value haimei-panel__stat-value--rejected">{{ summary.rejected }}</span>
        <span class="haimei-panel__stat-label">已驳回</span>
      </div>
    </div>

    <div class="haimei-panel__sections">
      <div class="haimei-panel__section">
        <h4 class="haimei-panel__section-title">📋 工作流步骤</h4>
        <div class="haimei-panel__step-list">
          <div v-for="step in steps" :key="step.step_number"
               class="haimei-panel__step"
               :class="[`haimei-panel__step--${step.status}`]">
            <div class="haimei-panel__step-header">
              <span class="haimei-panel__step-num">#{{ step.step_number }}</span>
              <span class="haimei-panel__step-name">{{ step.step_name }}</span>
              <el-tag :type="stepTagType(step.status)" size="small" effect="plain">
                {{ step.status_label }}
              </el-tag>
            </div>
            <div class="haimei-panel__step-meta">
              <span class="haimei-panel__step-agent">
                {{ step.executor_icon }} {{ step.executor_name }}
              </span>
              <span v-if="step.supervisor" class="haimei-panel__step-supervisor">
                👩‍💼 海梅监督
              </span>
            </div>
            <el-progress :percentage="step.progress" size="small"
                         :status="step.progress === 100 ? 'success' : undefined"
                         :stroke-width="4" />
          </div>
        </div>
      </div>

      <div class="haimei-panel__section">
        <h4 class="haimei-panel__section-title">🤖 Agent健康状态</h4>
        <div class="haimei-panel__agent-list">
          <div v-for="agent in agents" :key="agent.agent"
               class="haimei-panel__agent"
               :class="{ 'haimei-panel__agent--haimei': agent.is_haimei }">
            <span class="haimei-panel__agent-icon">{{ agent.icon }}</span>
            <span class="haimei-panel__agent-name">{{ agent.name }}</span>
            <el-tag :type="healthTagType(agent.health)" size="small">
              {{ agent.health_label }}
            </el-tag>
            <span v-if="agent.in_progress_step" class="haimei-panel__agent-step">
              步骤{{ agent.in_progress_step }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="haimei-panel__footer">
      <span class="haimei-panel__footer-text">👩‍💼 海梅全程监督 | 点击刷新按钮获取最新数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/modules/workflow'
import { boardApi } from '@/api/modules/board'

const props = defineProps<{
  projectId?: string
  boardId: string
}>()

const loading = ref(false)
const resolvedProjectId = ref<string | null>(props.projectId || null)
const steps = ref<any[]>([])
const agents = ref<any[]>([])
const summary = ref<any>(null)
const haimeiMessage = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

async function resolveProjectId() {
  if (resolvedProjectId.value) return
  try {
    const res: any = await boardApi.detail(props.boardId)
    const body = res.data || res
    const boardObj = body.board || body
    resolvedProjectId.value = boardObj.project_id || null
  } catch {
    // board may not exist yet
  }
}

async function refreshData() {
  await resolveProjectId()
  if (!resolvedProjectId.value) {
    loading.value = false
    return
  }

  loading.value = true
  try {
    const res: any = await workflowApi.getHaimeiBoardData(resolvedProjectId.value, props.boardId)
    const body = res.data || res || {}
    steps.value = body.steps || []
    agents.value = body.agents || []
    summary.value = body.summary || null
    haimeiMessage.value = body.haimei_message || ''
  } catch (e: any) {
    if (e?.status !== 401) {
      console.warn('海梅数据加载失败', e?.message)
    }
  } finally {
    loading.value = false
  }
}

function stepTagType(status: string): 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
    completed: 'success',
    in_progress: 'warning',
    qa_review: 'info',
    rejected: 'danger',
    pending: 'info',
  }
  return map[status] || 'info'
}

function healthTagType(health: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    healthy: 'success',
    busy: 'warning',
    error: 'danger',
    offline: 'danger',
    recovering: 'warning',
  }
  return map[health] || 'info'
}

onMounted(() => {
  refreshData()
  pollTimer = setInterval(refreshData, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style lang="scss" scoped>
.haimei-panel {
  background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
  border: 1px solid #e0e7ff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  font-size: 14px;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  &__title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__icon {
    font-size: 24px;
  }

  &__title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #4338ca;
  }

  &__actions {
    display: flex;
    gap: 4px;
  }

  &__message {
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 12px;
    font-size: 13px;
    color: #4338ca;
  }

  &__summary {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
  }

  &__stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: white;
    border-radius: 8px;
    padding: 8px 16px;
    flex: 1;
  }

  &__stat-value {
    font-size: 24px;
    font-weight: 700;
    color: #22c55e;

    &--active { color: #f59e0b; }
    &--review { color: #3b82f6; }
    &--rejected { color: #ef4444; }
  }

  &__stat-label {
    font-size: 12px;
    color: #6b7280;
  }

  &__sections {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  &__section-title {
    margin: 0 0 8px;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  &__step-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__step {
    background: white;
    border-radius: 8px;
    padding: 10px 12px;
    border-left: 3px solid #e5e7eb;

    &--completed { border-left-color: #22c55e; }
    &--in_progress { border-left-color: #f59e0b; }
    &--qa_review { border-left-color: #3b82f6; }
    &--rejected { border-left-color: #ef4444; }
  }

  &__step-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  &__step-num {
    font-weight: 700;
    color: #4338ca;
    font-size: 12px;
    min-width: 24px;
  }

  &__step-name {
    flex: 1;
    font-weight: 500;
    color: #1f2937;
    font-size: 13px;
  }

  &__step-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 6px;
  }

  &__agent-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 8px;
  }

  &__agent {
    display: flex;
    align-items: center;
    gap: 6px;
    background: white;
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;

    &--haimei {
      background: #eef2ff;
      border: 1px solid #c7d2fe;
    }
  }

  &__agent-icon { font-size: 18px; }
  &__agent-name { flex: 1; font-weight: 500; color: #1f2937; }
  &__agent-step { font-size: 11px; color: #9ca3af; }

  &__footer {
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px solid #e5e7eb;
  }

  &__footer-text {
    font-size: 12px;
    color: #9ca3af;
  }
}
</style>
