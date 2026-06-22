<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { workflowApi } from '@/api/modules/workflow'

const props = defineProps<{ projectId: string; stepNumber?: number | string }>()
const route = useRoute()
const router = useRouter()

const stepNumber = computed(() => {
  const raw = props.stepNumber || route.params.stepNumber
  return parseInt(String(raw)) || 4
})
const projectName = ref('')
const loading = ref(false)
const executing = ref(false)
const error = ref('')
const stageLog = ref<{ type: string; message: string }[]>([])
const liveContent = ref('')
const streamStatus = ref('')
const wsTimer = ref<ReturnType<typeof setTimeout> | null>(null)
let ws: WebSocket | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

// SEE streaming state for Step5
const seeMessages = ref<{ agent: string; phase: string; content: string; timestamp: number }[]>([])
const seePanelRef = ref<HTMLElement | null>(null)
const isStreaming = ref(false)
const currentPhase = ref('')
const fixRound = ref(0)
const seeAutoScroll = ref(true)

type StepStatus = 'pending' | 'in_progress' | 'qa_review' | 'completed' | 'rejected' | 'error'
const stepStatus = ref<StepStatus>('pending')

const stepNames: Record<number, string> = {
  2: '确认核心目标与搭建组织架构',
  3: '需求分析',
  4: '架构设计',
  5: '建立开发环境',
  6: '制订TDD测试用例计划',
  7: '编写TDD测试用例',
  8: '制订代码编写计划',
  9: '编写功能代码',
  10: '部署到测试环境',
  11: '全面测试',
  12: '安全审计',
  13: '部署到生产环境',
  14: '完善项目文档',
  15: '报告交付成果',
  16: '用户满意度确认与迭代',
}

const executorNames: Record<string, string> = {
  haimei: '海梅', houxing: '后兴', houwang: '后旺', houfa: '后发',
  houda: '后达', houfu: '后富', hougui: '后贵', hourong: '后荣', houhua: '后华',
  null: '用户',
}

const statusLabelMap: Record<string, string> = {
  pending: '未开始', in_progress: '执行中', qa_review: '待检验',
  completed: '已完成', rejected: '已退回', error: '出错',
}

const statusTagType: Record<string, string> = {
  pending: 'info', in_progress: 'warning', qa_review: 'warning',
  completed: 'success', rejected: 'danger', error: 'danger',
}

const prevStep = computed(() => stepNumber.value - 1)
const nextStep = computed(() => stepNumber.value + 1)

async function loadStatus() {
  loading.value = true
  try {
    projectName.value = (route.query.name as string) || ''
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    const steps = data?.steps || {}
    const stepKey = String(stepNumber.value)
    const stepRow = steps[stepKey] || {}

    stepStatus.value = stepRow.status || 'pending'

    // Load artifacts
    const artKeyName = `step${stepNumber.value}`
    const artifacts: any = (data as any)?.[artKeyName] || {}

    // Extract content from artifacts
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

    // Auto-execute if pending and previous step is completed
    if (stepStatus.value === 'pending') {
      const prevKey = String(prevStep.value)
      const prevRow = steps[prevKey] || {}
      if (prevRow.status === 'completed') {
        // 前置步骤已完成，自动执行当前步骤
        stageLog.value.push({ type: 'stage', message: `🚀 步骤${prevStep.value}已就绪，自动执行步骤${stepNumber.value}...` })
        setTimeout(() => handleExecute(), 500)
      } else {
        stageLog.value.push({
          type: 'stage',
          message: `⚠️ 步骤${prevStep.value}状态为"${prevRow.status || 'pending'}"，需先完成步骤${prevStep.value}才能开始。`,
        })
      }
    }

    // Start polling / WS if in_progress
    if (stepStatus.value === 'in_progress') {
      if (stepNumber.value === 5) {
        // Step5 in_progress: connect WS and send execute to start/resume
        isStreaming.value = true
        seeMessages.value = []
        currentPhase.value = 'initializing'
        fixRound.value = 0
        streamStatus.value = '🚀 正在执行...'
        executing.value = true
        error.value = ''
        stageLog.value = []
        stageLog.value.push({ type: 'stage', message: `🚀 自动执行步骤5...` })
        connectWsStep5(() => {
          stepStatus.value = 'in_progress'
        })
      } else {
        connectWs()
      }
      startPolling()
      resetStuckTimer()
    }
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function getProgressWsUrl(): string {
  const token = localStorage.getItem('access_token') || ''
  const port = import.meta.env.VITE_BACKEND_PORT || '9000'
  const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
  if (stepNumber.value <= 4) return `${base}/api/step4/progress/${props.projectId}?token=${encodeURIComponent(token)}`
  return `${base}/api/step${stepNumber.value}/progress/${props.projectId}?token=${encodeURIComponent(token)}`
}

function resetStuckTimer() {
  if (wsTimer.value) clearTimeout(wsTimer.value)
  wsTimer.value = setTimeout(() => {
    if (stepStatus.value === 'in_progress') {
      stageLog.value.push({
        type: 'error',
        message: '⚠️ 长时间未收到实时消息，Agent可能已中断。请点"重新执行"恢复。',
      })
    }
  }, 120000)
}

function connectWs() {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    ws = new WebSocket(getProgressWsUrl())
    ws.onmessage = (event) => {
      try {
        resetStuckTimer()
        const msg = JSON.parse(event.data)
        if (msg.type === 'stage' || msg.type === 'progress') {
          stageLog.value.push({ type: msg.type, message: msg.message })
        } else if (msg.type === 'content') {
          liveContent.value += msg.content
        } else if (msg.type === 'done') {
          stageLog.value.push({ type: 'done', message: msg.message })
          streamStatus.value = msg.message
          clearAllTimers()
          setTimeout(() => loadStatus(), 2000)
        } else if (msg.type === 'error') {
          stageLog.value.push({ type: 'error', message: msg.message })
        }
      } catch {}
    }
    ws.onclose = () => { ws = null }
    ws.onerror = () => { ws = null }
  } catch {}
}

function clearAllTimers() {
  if (wsTimer.value) { clearTimeout(wsTimer.value); wsTimer.value = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await workflowApi.getStatus(props.projectId) as any
      const data = res?.data || res
      const stepKey = String(stepNumber.value)
      const prevStepKey = String(prevStep.value)
      const stepRow = data?.steps?.[stepKey]
      const prevRow = data?.steps?.[prevStepKey]

      if (stepRow?.status === 'completed' || stepRow?.status === 'qa_review') {
        clearAllTimers()
        await loadStatus()
      } else if (stepRow?.status === 'pending' && prevRow?.status !== 'completed') {
        stageLog.value.push({
          type: 'stage',
          message: `⏸️ 步骤${stepNumber.value}暂时无法执行，前置步骤${prevStep.value}尚未完成（当前"${prevRow?.status}"）`,
        })
        clearAllTimers()
      }
    } catch {}
  }, 5000)
}

async function handleExecute() {
  executing.value = true
  error.value = ''
  stageLog.value = []
  stageLog.value.push({ type: 'stage', message: `🚀 正在启动步骤${stepNumber.value}...` })

  // Step 5: SEE-style WS execute (inline, streaming)
  if (stepNumber.value === 5) {
    seeMessages.value = []
    isStreaming.value = true
    currentPhase.value = 'initializing'
    fixRound.value = 0
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
    return
  }

  // Other steps: via haimei auto-advance
  try {
    const res = await workflowApi.haimeiAutoAdvance(props.projectId)
    const data = res?.data || res

    const statusRes = await workflowApi.getStatus(props.projectId) as any
    const statusData = statusRes?.data || statusRes
    const stepRow = statusData?.steps?.[String(stepNumber.value)]

    if (stepRow?.status === 'in_progress') {
      executing.value = false
      ElMessage.success(`步骤${stepNumber.value}已启动`)
      stepStatus.value = 'in_progress'
      streamStatus.value = '🚀 正在执行...'
      connectWs()
      startPolling()
      resetStuckTimer()
    } else if (stepRow?.status === 'completed' || stepRow?.status === 'qa_review') {
      executing.value = false
      ElMessage.success(`步骤${stepNumber.value}已完成`)
      await loadStatus()
    } else {
      executing.value = false
      const prevStatus = statusData?.steps?.[String(prevStep.value)]?.status
      if (prevStatus !== 'completed') {
        error.value = `无法执行：前置步骤${prevStep.value}状态为"${prevStatus}"，需先完成前一步。\n海梅提示：${data?.haimei_message || '请检查项目状态'}`
      } else {
        error.value = '推进失败，请刷新后重试'
      }
    }
  } catch (e: any) {
    executing.value = false
    error.value = e?.message || '与后端通信失败'
  }
}

// Step 5 SEE-style WS: connect then send execute
// isResume: if true, don't send execute, just listen
function connectWsStep5(onOpen: () => void, isResume: boolean = false) {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  try {
    const token = localStorage.getItem('access_token') || ''
    const port = import.meta.env.VITE_BACKEND_PORT || '9000'
    const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
    ws = new WebSocket(`${base}/api/step5/progress/${props.projectId}?token=${encodeURIComponent(token)}`)

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

let seeBuffer = ''

function handleSeeMessage(msg: any, isResume: boolean) {
  if (msg.type === 'progress') {
    // Parse phase from content
    const content = msg.content || ''

    // Detect phase changes
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
      // Streaming content from houfu
      seeBuffer += content
      updateSeeStreamingBuffer(seeBuffer)
    }

    // Also update liveContent for preview
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
  // Update the last streaming entry's content
  if (seeMessages.value.length > 0) {
    const last = seeMessages.value[seeMessages.value.length - 1]
    if (last.phase === 'generating' || last.phase === 'initializing') {
      // Show accumulated buffer periodically
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

async function handleGoPrev() {
  if (prevStep.value === 4) {
    router.push({ name: 'Step4', params: { projectId: props.projectId }, query: { name: projectName.value } })
  } else if (prevStep.value >= 5) {
    router.push({ name: 'WorkflowStep', params: { projectId: props.projectId, stepNumber: prevStep.value }, query: { name: projectName.value } })
  }
}

async function handleGoNext() {
  if (nextStep.value <= 4) {
    router.push({ name: 'Step4', params: { projectId: props.projectId }, query: { name: projectName.value } })
  } else if (nextStep.value <= 16) {
    router.push({ name: 'WorkflowStep', params: { projectId: props.projectId, stepNumber: nextStep.value }, query: { name: projectName.value } })
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
<div class="workflow-step-view" v-loading="loading">
  <div class="workflow-step-view__header">
    <div class="workflow-step-view__header-left">
      <el-button :icon="ArrowLeft" text @click="goBack">返回</el-button>
      <div>
        <h1>步骤{{ stepNumber }}：{{ stepNames[stepNumber] || `步骤${stepNumber}` }}</h1>
        <p class="workflow-step-view__subtitle">
          {{ projectName }}
          <el-tag :type="statusTagType[stepStatus] || 'info'" size="small" effect="dark" style="margin-left: 12px">
            {{ statusLabelMap[stepStatus] || stepStatus }}
          </el-tag>
        </p>
      </div>
    </div>
  </div>

  <el-alert v-if="error" :title="error" type="error" show-icon closable class="workflow-step-view__alert" @close="error = ''" />

  <!-- pending -->
  <div v-if="stepStatus === 'pending'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">⏳</div>
    <h2>准备执行：{{ stepNames[stepNumber] || `步骤${stepNumber}` }}</h2>
    <p>海梅将调度对应Agent执行此步骤。如果前置步骤已完成，点击"立即执行"即可启动。</p>
    <div class="workflow-step-view__action-row">
      <el-button type="primary" size="large" :loading="executing" @click="handleExecute">
        🚀 立即执行
      </el-button>
      <el-button plain size="large" @click="handleGoPrev">
        ← 回到步骤{{ prevStep }}
      </el-button>
    </div>
  </div>

  <!-- in_progress Step5: SEE-style real-time display -->
  <div v-if="stepStatus === 'in_progress' && stepNumber === 5" class="workflow-step-view__card workflow-step-view__card--executing">
    <!-- Status header -->
    <div class="workflow-step-view__see-header">
      <div class="workflow-step-view__see-status">
        <span class="workflow-step-view__see-dot" :class="isStreaming ? 'is-streaming' : ''"></span>
        <span>{{ streamStatus || 'Agent 正在工作中...' }}</span>
      </div>
      <div class="workflow-step-view__see-meta">
        <el-tag v-if="currentPhase === 'generating'" type="warning" effect="dark" size="small">🔧 后富生成中</el-tag>
        <el-tag v-else-if="currentPhase === 'qa_inspecting'" type="primary" effect="dark" size="small">🔍 后荣检验中</el-tag>
        <el-tag v-else-if="currentPhase === 'qa_passed'" type="success" effect="dark" size="small">✅ 检验通过</el-tag>
        <el-tag v-else-if="currentPhase === 'qa_failed'" type="danger" effect="dark" size="small">⚠️ 未通过</el-tag>
        <el-tag v-else-if="fixRound > 0" type="info" effect="plain" size="small">第 {{ fixRound }} 轮</el-tag>
      </div>
    </div>

    <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width: 400px; margin: 8px auto 16px" />

    <!-- SEE real-time stream panel -->
    <div class="workflow-step-view__see-panel" ref="seePanelRef">
      <div class="workflow-step-view__see-panel-header">
        <span>📡 后富实时状态 (SEE Streaming)</span>
        <el-switch v-model="seeAutoScroll" size="small" active-text="自动滚动" />
      </div>
      <div class="workflow-step-view__see-messages">
        <div v-if="seeMessages.length === 0" class="workflow-step-view__see-empty">
          等待实时消息...
        </div>
        <div v-for="(msg, i) in seeMessages" :key="i" class="workflow-step-view__see-msg" :class="msg.phase">
          <div class="workflow-step-view__see-msg-header">
            <span class="workflow-step-view__see-msg-avatar" :class="'agent-' + msg.agent.toLowerCase().replace(/[^\p{L}]/gu, '')">
              {{ msg.agent === '后富' ? '🔧' : msg.agent === '后荣' ? '🔍' : 'ℹ️' }}
            </span>
            <span class="workflow-step-view__see-msg-agent">{{ msg.agent }}</span>
            <span class="workflow-step-view__see-msg-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="workflow-step-view__see-msg-body">{{ msg.content }}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- in_progress other steps -->
  <div v-if="stepStatus === 'in_progress' && stepNumber !== 5" class="workflow-step-view__card workflow-step-view__card--executing">
    <div class="workflow-step-view__card-icon">⚙️</div>
    <h2>执行中...</h2>
    <p class="workflow-step-view__executing-status">{{ streamStatus || 'Agent 正在工作中...' }}</p>
    <el-progress :percentage="100" :stroke-width="4" status="warning" indeterminate style="max-width: 400px; margin: 16px auto" />
  </div>

  <!-- qa_review -->
  <div v-if="stepStatus === 'qa_review'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">🔍</div>
    <h2>等待 QA 检验</h2>
    <p>步骤执行完成，等待检验通过后进入下一步</p>
  </div>

  <!-- completed -->
  <div v-if="stepStatus === 'completed'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">✅</div>
    <h2>已完成</h2>
    <div class="workflow-step-view__action-row">
      <el-button size="large" @click="handleGoNext">
        进入步骤{{ nextStep }} →
      </el-button>
    </div>
  </div>

  <!-- rejected / error -->
  <div v-if="stepStatus === 'rejected' || stepStatus === 'error'" class="workflow-step-view__card">
    <div class="workflow-step-view__card-icon">❌</div>
    <h2>{{ statusLabelMap[stepStatus] || stepStatus }}</h2>
    <div class="workflow-step-view__action-row">
      <el-button type="primary" size="large" :loading="executing" @click="handleExecute">
        🔄 重新执行
      </el-button>
      <el-button plain size="large" @click="handleGoPrev">
        ← 回到步骤{{ prevStep }}
      </el-button>
    </div>
  </div>

  <!-- 执行日志 -->
  <div v-if="stageLog.length" class="workflow-step-view__log">
    <h3>📋 执行日志</h3>
    <div class="workflow-step-view__log-scroll">
      <div v-for="(msg, i) in stageLog" :key="i" class="workflow-step-view__log-msg" :class="msg.type">
        <span>
          {{ msg.type === 'stage' ? '📌' : msg.type === 'progress' ? '⏳' : msg.type === 'done' ? '✅' : '❌' }}
        </span>
        <span style="white-space: pre-wrap">{{ msg.message }}</span>
      </div>
    </div>
  </div>

  <!-- 产物预览 -->
  <div v-if="liveContent.trim()" class="workflow-step-view__content">
    <h3>📄 产物预览</h3>
    <pre>{{ liveContent }}</pre>
  </div>
</div>
</template>

<style scoped lang="scss">
@keyframes see-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

.workflow-step-view {
  max-width: 1100px; margin: 0 auto; padding: 32px 24px;

  &__header {
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px;
    &-left { display: flex; align-items: flex-start; gap: 16px; h1 { margin: 0; font-size: 24px; font-weight: 600; } }
  }
  &__subtitle { margin: 4px 0 0; color: #909399; font-size: 14px; }
  &__alert { margin-bottom: 16px; }
  &__card { text-align: center; padding: 40px 24px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; }
  &__card-icon { font-size: 48px; line-height: 1; }
  &__action-row { display: flex; gap: 12px; justify-content: center; margin-top: 24px; }
  &__executing-status { font-size: 14px; color: #e6a23c; font-weight: 500; }
  &--executing { border-color: #e6a23c; background: #fdf6ec; }

  // SEE streaming panel (Step5)
  &__see-header {
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 8px;
  }
  &__see-status { display: flex; align-items: center; gap: 8px; font-weight: 500; color: #303133; }
  &__see-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #909399;
    &.is-streaming { background: #67c23a; animation: see-pulse 1.5s ease-in-out infinite; }
  }
  &__see-meta { display: flex; gap: 8px; align-items: center; }

  &__see-panel {
    margin-top: 16px; border: 1px solid #e4e7ed; border-radius: 8px; overflow: hidden; background: #fff;
  }
  &__see-panel-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; background: #f5f7fa; border-bottom: 1px solid #e4e7ed; font-size: 13px; font-weight: 500;
  }
  &__see-messages {
    max-height: 500px; overflow-y: auto; padding: 8px;
  }
  &__see-empty {
    padding: 32px; text-align: center; color: #909399; font-size: 14px;
  }
  &__see-msg {
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
  &__see-msg-header {
    display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 12px;
  }
  &__see-msg-avatar {
    font-size: 14px; width: 20px; text-align: center;
  }
  &__see-msg-agent {
    font-weight: 600; color: #303133;
  }
  &__see-msg-time {
    color: #909399; margin-left: auto; font-size: 11px;
  }
  &__see-msg-body {
    font-size: 13px; color: #606266; line-height: 1.6; white-space: pre-wrap; word-break: break-word;
  }

  &__log { margin-top: 24px; padding: 16px; background: #fafafa; border: 1px solid #e4e7ed; border-radius: 8px;
    h3 { margin: 0 0 12px; font-size: 16px; }
  }
  &__log-scroll { max-height: 400px; overflow-y: auto; }
  &__log-msg { padding: 6px 0; font-size: 13px; border-bottom: 1px solid #f0f0f0; display: flex; gap: 8px; align-items: flex-start;
    &.error { color: #f56c6c; }
    &.done { color: #67c23a; font-weight: 500; }
  }

  &__content { margin-top: 24px; padding: 16px; background: #fff; border: 1px solid #e4e7ed; border-radius: 8px;
    h3 { margin: 0 0 12px; font-size: 16px; }
    pre { font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; line-height: 1.6; }
  }
}
</style>
