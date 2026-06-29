<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/modules/workflow'
import WorkflowStepBase from '@/components/WorkflowStepBase.vue'

const props = defineProps<{ projectId: string }>()
const router = useRouter()
const route = useRoute()

const stepNumber = 5

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
  5: '建立开发环境',
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

const isStreaming = ref(false)
const seeMessages = ref<{ agent: string; phase: string; content: string; timestamp: number }[]>([])
const currentPhase = ref('')
const fixRound = ref(0)
const seeAutoScroll = ref(true)
const seePanelRef = ref<HTMLElement | null>(null)
let seeBuffer = ''

function getProgressWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const port = import.meta.env.VITE_BACKEND_PORT || '9000'
  const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
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

    if (stepStatus.value === 'pending') {
      const prevKey = String(prevStep.value)
      const prevRow = steps[prevKey] || {}
      if (prevRow.status === 'completed') {
        stageLog.value.push({ type: 'stage', message: `🚀 步骤${prevStep.value}已就绪，自动执行步骤${stepNumber}...` })
        setTimeout(() => handleExecute(), 500)
      } else {
        stageLog.value.push({
          type: 'stage',
          message: `⚠️ 步骤${prevStep.value}状态为"${prevRow.status || 'pending'}"，需先完成步骤${prevStep.value}才能开始。`,
        })
      }
    }

    if (stepStatus.value === 'in_progress') {
      isStreaming.value = true
      seeMessages.value = []
      currentPhase.value = 'initializing'
      fixRound.value = 0
      streamStatus.value = '🚀 正在执行...'
      executing.value = true
      error.value = ''
      stageLog.value = []
      stageLog.value.push({ type: 'stage', message: `🚀 自动执行步骤${stepNumber}...` })
      connectWsStep5(() => {
        stepStatus.value = 'in_progress'
      })
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

function connectWsStep5(onOpen: () => void, isResume: boolean = false) {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    ws = new WebSocket(getProgressWsUrl())
    ws.onmessage = (event) => {
      try {
        resetStuckTimer()
        const msg = JSON.parse(event.data)
        handleSeeMessage(msg, isResume)
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
    ws.onclose = () => {
      ws = null
      if (isStreaming.value) {
        isStreaming.value = false
      }
    }
    ws.onerror = () => {
      executing.value = false
      isStreaming.value = false
      error.value = 'WS 连接失败'
    }
  } catch {
    executing.value = false
    isStreaming.value = false
    error.value = 'WS 初始化失败'
  }
}

function handleSeeMessage(msg: any, isResume: boolean) {
  if (msg.type === 'progress') {
    const content = msg.content || ''

    if (content.includes('后富正在生成') || content.includes('后富正在修复')) {
      const roundMatch = content.match(/第(\d+)轮/)
      if (roundMatch) {
        fixRound.value = parseInt(roundMatch[1])
      }
      currentPhase.value = 'generating'
      stageLog.value.push({ type: 'progress', message: content })
      addSeeMessage('后富', 'generating', content)
      seeBuffer = ''
    } else if (content.includes('正在建立开发环境')) {
      currentPhase.value = 'initializing'
      stageLog.value.push({ type: 'progress', message: content })
      addSeeMessage('系统', 'initializing', content)
      seeBuffer = ''
    } else if (content.includes('后荣正在检验') || content.includes('后荣重新检验')) {
      currentPhase.value = 'qa_inspecting'
      stageLog.value.push({ type: 'progress', message: content })
      addSeeMessage('后荣', 'qa_inspecting', content)
      seeBuffer = ''
    } else if (content.includes('通过') && (content.includes('检验') || content.includes('后荣'))) {
      currentPhase.value = 'qa_passed'
      addSeeMessage('系统', 'qa_passed', content)
    } else if (content.includes('未通过')) {
      currentPhase.value = 'qa_failed'
      addSeeMessage('系统', 'qa_failed', content)
    } else if (content.includes('❌') || content.includes('⚠️')) {
      addSeeMessage('系统', 'warning', content)
    } else if (content.trim()) {
      seeBuffer += content
      updateSeeStreamingBuffer(seeBuffer)
    }

    liveContent.value += content

  } else if (msg.type === 'done') {
    stageLog.value.push({ type: 'done', message: msg.message })
    streamStatus.value = msg.message
    addSeeMessage('系统', 'done', msg.message)
    executing.value = false
    isStreaming.value = false
    clearAllTimers()
    setTimeout(() => loadStatus(), 2000)

  } else if (msg.type === 'error') {
    stageLog.value.push({ type: 'error', message: msg.message })
    addSeeMessage('系统', 'error', msg.message)
    executing.value = false
    isStreaming.value = false
  }
}

function addSeeMessage(agent: string, phase: string, content: string) {
  seeMessages.value.push({
    agent,
    phase,
    content,
    timestamp: Date.now(),
  })
  scrollToBottom()
}

function updateSeeStreamingBuffer(buffer: string) {
  if (seeMessages.value.length > 0) {
    const last = seeMessages.value[seeMessages.value.length - 1]
    if (last.phase === 'generating' || last.phase === 'initializing') {
      seeBuffer = buffer
      scrollToBottom()
    }
  }
}

async function scrollToBottom() {
  if (seeAutoScroll.value && seePanelRef.value) {
    await nextTick()
    seePanelRef.value.scrollTop = seePanelRef.value.scrollHeight
  }
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

async function handleExecute() {
  executing.value = true
  error.value = ''
  stageLog.value = []
  seeMessages.value = []
  isStreaming.value = true
  currentPhase.value = 'initializing'
  fixRound.value = 0
  stageLog.value.push({ type: 'stage', message: `🚀 正在启动步骤${stepNumber}...` })

  connectWsStep5(() => {
    try {
      ws?.send(JSON.stringify({ action: 'execute' }))
      stepStatus.value = 'in_progress'
      streamStatus.value = '🚀 正在执行...'
      startPolling()
      resetStuckTimer()
    } catch (e: any) {
      executing.value = false
      isStreaming.value = false
      error.value = e?.message || 'WS 发送失败'
    }
  })
}

async function handleGoPrev() {
  if (prevStep.value === 4) {
    router.push({ name: 'Step4', params: { projectId: props.projectId }, query: { name: projectName.value } })
  } else if (prevStep.value >= 2) {
    router.push({ name: `Step${prevStep.value}`, params: { projectId: props.projectId }, query: { name: projectName.value } })
  }
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
    <div class="step5-see-header">
      <div class="step5-see-status">
        <span class="step5-see-dot" :class="isStreaming ? 'is-streaming' : ''"></span>
        <span>{{ streamStatus || 'Agent 正在工作中...' }}</span>
      </div>
      <div class="step5-see-meta">
        <el-tag v-if="currentPhase === 'generating'" type="warning" effect="dark" size="small">🔧 后富生成中</el-tag>
        <el-tag v-else-if="currentPhase === 'qa_inspecting'" type="primary" effect="dark" size="small">🔍 后荣检验中</el-tag>
        <el-tag v-else-if="currentPhase === 'qa_passed'" type="success" effect="dark" size="small">✅ 检验通过</el-tag>
        <el-tag v-else-if="currentPhase === 'qa_failed'" type="danger" effect="dark" size="small">⚠️ 未通过</el-tag>
        <el-tag v-else-if="fixRound > 0" type="info" effect="plain" size="small">第 {{ fixRound }} 轮</el-tag>
      </div>
    </div>

    <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width: 400px; margin: 8px auto 16px" />

    <div class="step5-see-panel" ref="seePanelRef">
      <div class="step5-see-panel-header">
        <span>📡 后富实时状态 (SEE Streaming)</span>
        <el-switch v-model="seeAutoScroll" size="small" active-text="自动滚动" />
      </div>
      <div class="step5-see-messages">
        <div v-if="seeMessages.length === 0" class="step5-see-empty">等待实时消息...</div>
        <div v-for="(msg, i) in seeMessages" :key="i" class="step5-see-msg" :class="msg.phase">
          <div class="step5-see-msg-header">
            <span class="step5-see-msg-avatar">
              {{ msg.agent === '后富' ? '🔧' : msg.agent === '后荣' ? '🔍' : 'ℹ️' }}
            </span>
            <span class="step5-see-msg-agent">{{ msg.agent }}</span>
            <span class="step5-see-msg-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="step5-see-msg-body">{{ msg.content }}</div>
        </div>
      </div>
    </div>
  </template>
</WorkflowStepBase>
</template>

<style scoped lang="scss">
@keyframes see-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.step5-see-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 8px;
}
.step5-see-status { display: flex; align-items: center; gap: 8px; font-weight: 500; color: #303133; }
.step5-see-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #909399;
  &.is-streaming { background: #67c23a; animation: see-pulse 1.5s ease-in-out infinite; }
}
.step5-see-meta { display: flex; gap: 8px; align-items: center; }

.step5-see-panel {
  margin-top: 16px; border: 1px solid #e4e7ed; border-radius: 8px; overflow: hidden; background: #fff;
}
.step5-see-panel-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; background: #f5f7fa; border-bottom: 1px solid #e4e7ed; font-size: 13px; font-weight: 500;
}
.step5-see-messages {
  max-height: 500px; overflow-y: auto; padding: 8px;
}
.step5-see-empty {
  padding: 32px; text-align: center; color: #909399; font-size: 14px;
}
.step5-see-msg {
  padding: 8px 12px; margin-bottom: 4px; border-radius: 6px;
  &.generating { background: #fff7ed; }
  &.qa_inspecting { background: #eff6ff; }
  &.qa_passed { background: #f0fdf4; }
  &.qa_failed { background: #fef2f2; }
  &.error { background: #fef2f2; }
  &.done { background: #f0fdf4; font-weight: 500; }
  &.initializing { background: #f9fafb; }
  &.warning { background: #fff7ed; }
}
.step5-see-msg-header {
  display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 12px;
}
.step5-see-msg-avatar { font-size: 14px; width: 20px; text-align: center; }
.step5-see-msg-agent { font-weight: 600; color: #303133; }
.step5-see-msg-time { color: #909399; margin-left: auto; font-size: 11px; }
.step5-see-msg-body {
  font-size: 13px; color: #606266; line-height: 1.6; white-space: pre-wrap; word-break: break-word;
}
</style>
