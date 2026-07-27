<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/modules/workflow'
import WorkflowStepBase from '@/components/WorkflowStepBase.vue'

const props = defineProps<{ projectId: string }>()
const router = useRouter()
const route = useRoute()

const stepNumber = 6

const projectName = ref('')
const loading = ref(false)
const executing = ref(false)
const error = ref('')
const stageLog = ref<{ type: string; message: string }[]>([])
const liveContent = ref('')
const streamStatus = ref('')
const haimeiPrompt = ref('')
const showPrompt = ref(false)
let ws: WebSocket | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null
let wsTimer: ReturnType<typeof setTimeout> | null = null

const stepStatus = ref<'pending' | 'in_progress' | 'qa_review' | 'completed' | 'rejected' | 'error'>('pending')

const stepNames: Record<number, string> = {
  6: '制订TDD测试用例计划',
}

const statusLabelMap: Record<string, string> = {
  pending: '未开始', in_progress: '执行中', qa_review: '待检验',
  completed: '已完成', rejected: '已退回', error: '出错',
}

const statusTagType: Record<string, string> = {
  pending: 'info', in_progress: 'warning', qa_review: 'warning',
  completed: 'success', rejected: 'danger', error: 'danger',
}

const prevStep = computed(() => stepNumber - 1)
const nextStep = computed(() => stepNumber + 1)
const stepName = computed(() => stepNames[stepNumber] || `步骤${stepNumber}`)

const streamBodyRef = ref<HTMLElement | null>(null)

watch(liveContent, async () => {
  await nextTick()
  if (streamBodyRef.value) {
    streamBodyRef.value.scrollTop = streamBodyRef.value.scrollHeight
  }
})

const step6Prompt = ref('')
const step6Round = ref(0)
const step6TotalRounds = ref(10)
const step6ShowPrompt = ref(false)

interface CaseResult {
  case_id: string
  title: string
  passed: boolean
  score: number
  feedback: string
}
const caseResults = ref<CaseResult[]>([])

function getProgressWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const port = import.meta.env.VITE_BACKEND_PORT || '9000'
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const base = import.meta.env.VITE_WS_BASE_URL || `${protocol}//${location.hostname}:${port}`
  return `${base}/api/step${stepNumber}/progress/${props.projectId}?token=${encodeURIComponent(token)}`
}

function resetStuckTimer() {
  if (wsTimer) clearTimeout(wsTimer)
    wsTimer = setTimeout(() => {
    if (stepStatus.value === 'in_progress') {
      stageLog.value.push({
        type: 'error',
        message: '⚠️ 长时间未收到实时消息，Agent可能已中断。请点"重新执行"恢复。',
      })
    }
  }, 120000)
}

function clearAllTimers() {
  if (wsTimer) { clearTimeout(wsTimer); wsTimer = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await workflowApi.getStatus(props.projectId) as any
      const data = res?.data || res
      const stepKey = String(stepNumber)
      const prevStepKey = String(prevStep.value)
      const stepRow = data?.steps?.[stepKey]
      const prevRow = data?.steps?.[prevStepKey]

      if (stepRow?.status === 'completed' || stepRow?.status === 'qa_review') {
        clearAllTimers()
        await loadStatus()
        if (stepStatus.value === 'completed') {
          const next = stepNumber + 1
          setTimeout(() => {
            router.push({ name: `Step${next}`, params: { projectId: props.projectId }, query: { name: projectName.value } })
          }, 2000)
        }
      } else if (stepRow?.status === 'pending' && prevRow?.status !== 'completed') {
        stageLog.value.push({
          type: 'stage',
          message: `⏸️ 步骤${stepNumber}暂时无法执行，前置步骤${prevStep.value}尚未完成（当前"${prevRow?.status}"）`,
        })
        clearAllTimers()
      }
    } catch {}
  }, 5000)
}

async function loadStatus() {
  loading.value = true
  try {
    projectName.value = (route.query.name as string) || ''
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    const steps = data?.steps || {}
    const stepKey = String(stepNumber)
    const stepRow = steps[stepKey] || {}

    stepStatus.value = stepRow.status || 'pending'

    const artKeyName = `step${stepNumber}`
    const artifacts: any = (data as any)?.[artKeyName] || {}

    if (stepStatus.value === 'qa_review' && artifacts.qa_passed) {
      stepStatus.value = 'completed'
    }

    if (stepStatus.value === 'in_progress') {
      step6Prompt.value = ''
      step6Round.value = 0
      step6ShowPrompt.value = false
    }

    const contentKeys = ['design_doc', 'content', 'env_info', 'tdd_plan', 'code',
      'tdd_cases', 'code_plan', 'test_report', 'security_report',
      'project_docs', 'delivery_report', 'deployment_log', 'production_log']
    for (const key of contentKeys) {
      if (artifacts[key]) {
        liveContent.value = typeof artifacts[key] === 'string' ? artifacts[key] : JSON.stringify(artifacts[key], null, 2)
        break
      }
    }

    if (artifacts.message) {
      stageLog.value.push({ type: 'stage', message: artifacts.message })
    }

    const hasTddPlan = !!(artifacts.tdd_plan || artifacts.qa_passed)
    const hasProgress = !!(artifacts.current_fix_round || artifacts.convergence?.length)

    if (hasTddPlan) {
      if (stepStatus.value === 'pending' || stepStatus.value === 'in_progress') {
        stepStatus.value = 'completed'
        stageLog.value.push({ type: 'stage', message: `✅ TDD计划已生成，步骤${stepNumber}已完成。` })
        const nextStepNum = stepNumber + 1
        if (nextStepNum <= 16) {
          clearAllTimers()
          setTimeout(() => {
            router.push({ name: `Step${nextStepNum}`, params: { projectId: props.projectId }, query: { name: projectName.value } })
          }, 2000)
        }
        return
      }
    } else if (stepStatus.value === 'pending') {
      const prevKey = String(prevStep.value)
      const prevRow = steps[prevKey] || {}
      if (prevRow.status === 'completed') {
        if (hasProgress) {
          stageLog.value.push({ type: 'stage', message: `♻️ 检测到已有执行进度，恢复执行步骤${stepNumber}...` })
          setTimeout(() => handleExecute(), 500)
        } else {
          stageLog.value.push({ type: 'stage', message: `🚀 步骤${prevStep.value}已就绪，自动执行步骤${stepNumber}...` })
          setTimeout(() => handleExecute(), 500)
        }
      } else {
        stageLog.value.push({
          type: 'stage',
          message: `⚠️ 步骤${prevStep.value}状态为"${prevRow.status || 'pending'}"，需先完成步骤${prevStep.value}才能开始。`,
        })
      }
    } else if (stepStatus.value === 'in_progress') {
      if (hasProgress) {
        stageLog.value.push({ type: 'stage', message: `♻️ 检测到已有执行进度（第${artifacts.current_fix_round || '?'}轮），恢复执行...` })
        connectWsStep6(() => {
          stepStatus.value = 'in_progress'
          streamStatus.value = '♻️ 恢复执行中...'
        })
      } else {
        stageLog.value.push({ type: 'stage', message: `🔄 检测到步骤6中断，正在重新执行...` })
        connectWsStep6(() => {
          stepStatus.value = 'in_progress'
          streamStatus.value = '🚀 正在执行...'
        })
      }
      startPolling()
      resetStuckTimer()
    }

    if (stepStatus.value === 'completed') {
      const nextStepNum = stepNumber + 1
      if (nextStepNum <= 16) {
        clearAllTimers()
        setTimeout(() => {
          router.push({ name: `Step${nextStepNum}`, params: { projectId: props.projectId }, query: { name: projectName.value } })
        }, 2000)
        return
      }
    }
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function connectWsStep6(onOpen: () => void, isResume: boolean = false) {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    ws = new WebSocket(getProgressWsUrl())

    ws.onmessage = (event) => {
      try {
        resetStuckTimer()
        const msg = JSON.parse(event.data)
        if (msg.type === 'prompt') {
          step6Prompt.value = msg.prompt || ''
          step6Round.value = msg.round || 0
          step6TotalRounds.value = msg.total_rounds || 10
          step6ShowPrompt.value = false
        } else if (msg.type === 'stage' || msg.type === 'progress') {
          stageLog.value.push({ type: msg.type, message: msg.message })
          streamStatus.value = msg.message || streamStatus.value
        } else if (msg.type === 'content') {
          liveContent.value += msg.content
        } else if (msg.type === 'case_result') {
          const existing = caseResults.value.findIndex(r => r.case_id === msg.case_id)
          const entry = { case_id: msg.case_id, title: msg.title || '', passed: msg.passed, score: msg.score, feedback: msg.feedback || '' }
          if (existing >= 0) {
            caseResults.value[existing] = entry
          } else {
            caseResults.value.push(entry)
          }
        } else if (msg.type === 'done') {
          stageLog.value.push({ type: 'done', message: msg.message })
          streamStatus.value = msg.message
          clearAllTimers()
          setTimeout(() => loadStatus(), 2000)
        } else if (msg.type === 'error') {
          stageLog.value.push({ type: 'error', message: msg.message })
          clearAllTimers()
          executing.value = false
        }
      } catch {}
    }

    ws.onopen = () => {
      onOpen()
      if (!isResume) {
        try { ws?.send(JSON.stringify({ action: 'execute' })) } catch {}
      } else {
        try { ws?.send(JSON.stringify({ action: 'subscribe' })) } catch {}
      }
    }

    ws.onclose = () => { ws = null }
    ws.onerror = () => {
      executing.value = false
      error.value = 'WS 连接失败'
    }
  } catch {
    executing.value = false
    error.value = 'WS 初始化失败'
  }
}

async function handleExecute() {
  executing.value = true
  error.value = ''
  liveContent.value = ''
  stageLog.value = []
  stageLog.value.push({ type: 'stage', message: `🚀 正在启动步骤${stepNumber}...` })

  connectWsStep6(() => {
    stepStatus.value = 'in_progress'
    streamStatus.value = '🚀 海梅正在制订TDD计划...'
    startPolling()
    resetStuckTimer()
  })
}

async function handleGoPrev() {
  router.push({ name: 'Step5', params: { projectId: props.projectId }, query: { name: projectName.value } })
}

async function handleGoNext() {
  if (nextStep.value <= 16) {
    router.push({ name: `Step${nextStep.value}`, params: { projectId: props.projectId }, query: { name: projectName.value } })
  }
}

function goBack() {
  router.push({ name: 'ProjectDetail', params: { projectId: props.projectId } })
}

onMounted(() => loadStatus())
onUnmounted(() => {
  clearAllTimers()
  if (ws) { ws.onclose = null; ws.close(); ws = null }
})
</script>

<template>
<WorkflowStepBase
  :project-id="projectId"
  :step-number="stepNumber"
  :project-name="projectName"
  :loading="loading"
  :executing="executing"
  :error="error"
  :step-status="stepStatus"
  :step-name="stepName"
  :prev-step="prevStep"
  :next-step="nextStep"
  :stage-log="stageLog"
  :live-content="liveContent"
  :stream-status="streamStatus"
  :haimei-prompt="haimeiPrompt"
  :show-prompt="showPrompt"
  :status-label-map="statusLabelMap"
  :status-tag-type="statusTagType"
  @execute="handleExecute"
  @go-prev="handleGoPrev"
  @go-next="handleGoNext"
  @go-back="goBack"
  @toggle-prompt="showPrompt = !showPrompt"
  @close-error="error = ''"
>
  <template #in-progress>
    <div class="step6-header">
      <div class="step6-status">
        <span class="step6-dot is-streaming"></span>
        <span>{{ streamStatus || 'Agent 正在工作中...' }}</span>
      </div>
      <div class="step6-meta">
        <el-tag v-if="step6Round > 0" type="warning" effect="dark" size="small">
          第 {{ step6Round }} / {{ step6TotalRounds }} 轮
        </el-tag>
        <el-tag v-else type="info" effect="plain" size="small">准备中...</el-tag>
      </div>
    </div>

    <el-progress
      :percentage="step6TotalRounds > 0 ? Math.round((step6Round / step6TotalRounds) * 100) : 0"
      :stroke-width="6" status="warning" style="max-width: 400px; margin: 8px auto 16px"
    >
      <span v-if="step6Round > 0">{{ step6Round }} / {{ step6TotalRounds }}</span>
      <span v-else>准备中...</span>
    </el-progress>

    <div v-if="step6Prompt" class="step6-prompt">
      <div class="step6-prompt-header" @click="step6ShowPrompt = !step6ShowPrompt">
        <span>📝 海梅提示词（第{{ step6Round }}轮）</span>
        <el-icon :class="{ 'is-rotate': step6ShowPrompt }"><ArrowLeft /></el-icon>
      </div>
      <transition name="el-zoom-in-top">
        <div v-show="step6ShowPrompt" class="step6-prompt-body">
          <pre>{{ step6Prompt }}</pre>
        </div>
      </transition>
    </div>

    <div class="step6-stream">
      <h4>📄 海梅实时输出</h4>
      <div ref="streamBodyRef" class="step6-stream-body">
        <pre v-if="liveContent">{{ liveContent }}</pre>
        <div v-else class="step6-stream-waiting">⏳ 等待海梅生成TDD计划...</div>
      </div>
    </div>

    <div v-if="caseResults.length > 0" class="step6-results">
      <h4>🔍 hourong 检验结果（{{ caseResults.filter(r => r.passed).length }}/{{ caseResults.length }} 通过）</h4>
      <div class="step6-results-table">
        <div class="step6-results-row step6-results-header">
          <span class="col-status">状态</span>
          <span class="col-id">编号</span>
          <span class="col-title">标题</span>
          <span class="col-score">评分</span>
        </div>
        <div v-for="r in caseResults" :key="r.case_id"
          class="step6-results-row"
          :class="r.passed ? 'row-passed' : 'row-failed'">
          <span class="col-status">{{ r.passed ? '✅' : '❌' }}</span>
          <span class="col-id">{{ r.case_id }}</span>
          <span class="col-title" :title="r.feedback">{{ r.title }}</span>
          <span class="col-score">{{ r.score }}</span>
        </div>
      </div>
    </div>

    <div class="step6-rexec" v-if="!liveContent">
      <el-button type="warning" size="large" :loading="executing" @click="handleExecute">
        🔄 重新执行
      </el-button>
      <p class="step6-rexec-hint">长时间无响应时，可点击重新执行</p>
    </div>
  </template>
</WorkflowStepBase>
</template>

<style scoped lang="scss">
@keyframes see-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.step6-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 8px;
}
.step6-status { display: flex; align-items: center; gap: 8px; font-weight: 500; color: $text-primary; }
.step6-dot {
  width: 8px; height: 8px; border-radius: 50%; background: $text-muted;
  &.is-streaming { background: $secondary; animation: see-pulse 1.5s ease-in-out infinite; box-shadow: 0 0 6px rgba(52, 211, 153, 0.5); }
}
.step6-meta { display: flex; gap: 8px; align-items: center; }

.step6-prompt {
  margin-top: 16px; text-align: left;
  border: 1px solid $glass-border; border-radius: 10px; overflow: hidden;
  background: $glass-bg; backdrop-filter: $frosted-blur;
  &-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; background: $primary-dim; border-bottom: 1px solid $border-subtle;
    cursor: pointer; font-size: 13px; font-weight: 500; color: $text-primary;
    .el-icon { transition: transform 0.3s; &.is-rotate { transform: rotate(-90deg); } }
  }
  &-body {
    max-height: 300px; overflow-y: auto; padding: 12px;
    pre { font-family: $font-mono; font-size: 12px; white-space: pre-wrap; word-break: break-all; margin: 0; color: $text-secondary; }
  }
}

.step6-stream {
  margin-top: 16px; text-align: left;
  border: 1px solid $glass-border; border-radius: 10px; overflow: hidden;
  background: $glass-bg; backdrop-filter: $frosted-blur;
  h4 { margin: 0; padding: 10px 16px; background: rgba(255, 255, 255, 0.04); border-bottom: 1px solid $border-subtle; font-size: 13px; color: $text-primary; }
  &-body {
    max-height: 400px; overflow-y: auto; padding: 12px; color: $text-secondary;
    pre { font-family: $font-mono; font-size: 12px; white-space: pre-wrap; word-break: break-all; margin: 0; color: $text-secondary; }
  }
  &-waiting { text-align: center; color: $text-muted; padding: 40px 0; font-size: 14px; }
}

.step6-results {
  margin-top: 16px; text-align: left;
  border: 1px solid $glass-border; border-radius: 10px; overflow: hidden;
  background: $glass-bg; backdrop-filter: $frosted-blur;
  h4 { margin: 0; padding: 10px 16px; background: rgba(255, 255, 255, 0.04); border-bottom: 1px solid $border-subtle; font-size: 13px; color: $text-primary; }
  &-table { font-size: 12px; }
  &-row {
    display: flex; align-items: center; padding: 6px 16px; border-bottom: 1px solid $border-subtle;
    &:last-child { border-bottom: none; }
  }
  &-header { font-weight: 600; background: rgba(255, 255, 255, 0.03); color: $text-primary; }
  .col-status { width: 36px; flex-shrink: 0; text-align: center; }
  .col-id { width: 80px; flex-shrink: 0; font-family: $font-mono; color: $text-secondary; }
  .col-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .col-score { width: 50px; flex-shrink: 0; text-align: right; font-family: $font-mono; }
  .row-passed { background: $secondary-dim; }
  .row-failed { background: $danger-dim; }
}

.step6-rexec { text-align: center; margin-top: 20px; }
.step6-rexec-hint { font-size: 12px; color: $text-muted; margin-top: 6px; }
</style>
