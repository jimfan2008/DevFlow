<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { workflowApi } from '@/api/modules/workflow'
import { useWorkflowStep } from '@/composables/useWorkflowStep'
import WorkflowStepBase from '@/components/WorkflowStepBase.vue'

const props = defineProps<{ projectId: string }>()
const router = useRouter()

const {
  projectName, loading, executing, error, stageLog, liveContent,
  streamStatus, haimeiPrompt, showPrompt, stepStatus,
  prevStep, nextStep, stepName, statusLabelMap, statusTagType,
  loadStatus, startPolling, resetStuckTimer, clearAllTimers,
  handleGoPrev, handleGoNext, goBack, setWs,
} = useWorkflowStep({ projectId: props.projectId, stepNumber: 5, autoLoad: false })

// Step 5 SEE-specific state
const seeMessages = ref<{ agent: string; phase: string; content: string; timestamp: number }[]>([])
const seePanelRef = ref<HTMLElement | null>(null)
const isStreaming = ref(false)
const currentPhase = ref('')
const fixRound = ref(0)
const seeAutoScroll = ref(true)
let seeBuffer = ''

onMounted(() => loadStatusStep5())

// Override handleExecute for Step 5 SEE-style
async function handleExecute() {
  executing.value = true
  error.value = ''
  stageLog.value = []
  stageLog.value.push({ type: 'stage', message: '🚀 正在启动步骤5...' })

  seeMessages.value = []
  isStreaming.value = true
  currentPhase.value = 'initializing'
  fixRound.value = 0
  stepStatus.value = 'in_progress'
  streamStatus.value = '🚀 正在执行...'
  connectWsStep5(() => {
    startPolling(loadStatusStep5)
    resetStuckTimer()
  })
}

// Override loadStatus to handle Step 5 in_progress (SEE resume)
async function loadStatusStep5() {
  loading.value = true
  try {
    const route = useRoute()
    projectName.value = (route.query.name as string) || ''
    const res = await workflowApi.getStatus(props.projectId) as any
    const data = res?.data || res
    const steps = data?.steps || {}
    const stepRow = steps['5'] || {}

    const artifacts: any = (data as any)?.step5 || {}
    const artStatus = artifacts.status || ''

    // Determine effective status: if artifacts say "done" with qa_passed, step is complete
    console.log('[Step5] loadStatusStep5 artStatus=', artStatus, 'qa_passed=', artifacts.qa_passed, 'tableStatus=', stepRow.status)
    if (artStatus === 'done' && artifacts.qa_passed) {
      stepStatus.value = 'completed'
    } else if (artStatus === 'generating' || artStatus === 'error') {
      stepStatus.value = 'in_progress'
    } else if (stepRow.status === 'qa_review' && !artStatus) {
      // QA review in table but no artifacts — stale state, force pending
      stepStatus.value = 'pending'
    } else {
      stepStatus.value = stepRow.status || 'pending'
    }

    const contentKeys = ['env_info', 'content']
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
      const prevRow = steps['4'] || {}
      if (prevRow.status === 'completed') {
        stageLog.value.push({ type: 'stage', message: '🚀 步骤4已就绪，自动执行步骤5...' })
        setTimeout(() => handleExecute(), 500)
      } else {
        stageLog.value.push({ type: 'stage', message: `⚠️ 步骤4状态为"${prevRow.status || 'pending'}"，需先完成步骤4才能开始。` })
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
      stageLog.value.push({ type: 'stage', message: '🚀 自动执行步骤5...' })
      connectWsStep5(() => {}, true)
      startPolling(loadStatusStep5)
      resetStuckTimer()
    }

    // If step5_1 done but step5_2 not started (qa_passed but no setup_doc_path), resume chain
    if (stepStatus.value === 'completed' && artifacts.qa_passed && !artifacts.setup_doc_path) {
      // step5_1 passed, need to continue to step5_2 — reconnect WS to resume
      stepStatus.value = 'in_progress'
      isStreaming.value = true
      seeMessages.value = []
      currentPhase.value = 'initializing'
      streamStatus.value = '🔄 继续执行步骤5（阶段2）...'
      executing.value = true
      stageLog.value = []
      stageLog.value.push({ type: 'stage', message: '🔄 步骤5_1已完成，继续执行步骤5_2...' })
      connectWsStep5(() => {}, true)
      startPolling(loadStatusStep5)
      resetStuckTimer()
    }
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// Step 5 SEE-style WebSocket
function connectWsStep5(onOpen: () => void, isResume: boolean = false) {
  const token = localStorage.getItem('access_token') || ''
  const port = import.meta.env.VITE_BACKEND_PORT || '9000'
  const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
  const wsUrl = `${base}/api/step5/progress/${props.projectId}?token=${encodeURIComponent(token)}`

  const wsInstance = new WebSocket(wsUrl)
  setWs(wsInstance)

  wsInstance.onmessage = (event) => {
    try {
      resetStuckTimer()
      const msg = JSON.parse(event.data)
      handleSeeMessage(msg, isResume)
    } catch (e) {
      stageLog.value.push({ type: 'debug', message: `[DEBUG] WS消息解析失败: ${event.data?.slice(0,100)}` })
    }
  }

  wsInstance.onopen = () => {
    onOpen()
    try {
      wsInstance.send(JSON.stringify({ action: 'execute' }))
    } catch (e: any) {
      stageLog.value.push({ type: 'debug', message: `[DEBUG] ❌ 发送失败: ${e?.message}` })
    }
  }

  wsInstance.onclose = () => {
    setWs(null)
    if (isStreaming.value) {
      isStreaming.value = false
    }
  }
  wsInstance.onerror = () => {
    executing.value = false
    isStreaming.value = false
    error.value = 'WS 连接失败'
  }
}

function handleSeeMessage(msg: any, isResume: boolean) {
  if (msg.type === 'progress') {
    const content = msg.content || msg.message || ''
    const rawContent = msg.content || msg.message || ''

    if (content.includes('后富正在生成') || content.includes('后富正在修复')
        || content.includes('后富正在执行') || content.includes('后富正在建立')) {
      const roundMatch = content.match(/第(\d+)轮/)
      if (roundMatch) { fixRound.value = parseInt(roundMatch[1]) }
      currentPhase.value = 'generating'
      stageLog.value.push({ type: 'progress', message: content })
      addSeeMessage('后富', 'generating', content)
      seeBuffer = ''
    } else if (content.includes('正在建立开发环境')) {
      currentPhase.value = 'initializing'
      stageLog.value.push({ type: 'progress', message: content })
      addSeeMessage('系统', 'initializing', content)
      seeBuffer = ''
    } else if (content.includes('hourong') || content.includes('后荣正在检验') || content.includes('后荣重新检验')
        || content.includes('hourong 正在检验') || content.includes('hourong 第')) {
      currentPhase.value = 'qa_inspecting'
      stageLog.value.push({ type: 'progress', message: content })
      addSeeMessage('后荣', 'qa_inspecting', content)
      seeBuffer = ''
    } else if (content.includes('通过') && (content.includes('检验') || content.includes('后荣') || content.includes('hourong'))) {
      currentPhase.value = 'qa_passed'
      addSeeMessage('系统', 'qa_passed', content)
    } else if (content.includes('未通过')) {
      currentPhase.value = 'qa_failed'
      addSeeMessage('系统', 'qa_failed', content)
    } else if (content.includes('❌') || content.includes('⚠️') || content.includes('♻️')
        || content.includes('📋') || content.includes('📝') || content.includes('🔍')
        || content.includes('📤') || content.includes('🔧')) {
      addSeeMessage('系统', 'info', content)
    } else if (rawContent.trim()) {
      seeBuffer += rawContent
      updateSeeStreamingBuffer(seeBuffer)
    }

    if (msg.content && msg.content.trim()) {
      liveContent.value += msg.content
    }
  } else if (msg.type === 'prompt') {
    haimeiPrompt.value = msg.prompt || ''
    showPrompt.value = true
    stageLog.value.push({ type: 'progress', message: `📝 已收到提示词（第${msg.round || 1}轮）` })
    addSeeMessage('系统', 'prompt', `📝 已收到提示词（第${msg.round || 1}轮）`)
  } else if (msg.type === 'done') {
    stageLog.value.push({ type: 'done', message: msg.message })
    streamStatus.value = msg.message
    addSeeMessage('系统', 'done', msg.message)
    executing.value = false
    isStreaming.value = false
    clearAllTimers()
    setTimeout(() => {
      router.push({ name: 'Step6', params: { projectId: props.projectId }, query: { name: projectName.value } })
    }, 2000)
  } else if (msg.type === 'auto_next') {
    const nextStepNum = msg.step || 6
    stageLog.value.push({ type: 'done', message: msg.message })
    streamStatus.value = msg.message
    addSeeMessage('系统', 'done', msg.message)
    executing.value = false
    isStreaming.value = false
    clearAllTimers()
    setTimeout(() => {
      router.push({ name: `Step${nextStepNum}`, params: { projectId: props.projectId }, query: { name: projectName.value } })
    }, 2000)
  } else if (msg.type === 'timing') {
    stageLog.value.push({ type: 'timing', message: msg.message })
    addSeeMessage('系统', 'timing', msg.message)
  } else if (msg.type === 'error') {
    stageLog.value.push({ type: 'error', message: msg.message })
    addSeeMessage('系统', 'error', msg.message)
    executing.value = false
    isStreaming.value = false
  }
}

function addSeeMessage(agent: string, phase: string, content: string) {
  seeMessages.value.push({ agent, phase, content, timestamp: Date.now() })
  scrollToBottom()
}

function updateSeeStreamingBuffer(buffer: string) {
  if (seeMessages.value.length > 0) {
    const idx = seeMessages.value.length - 1
    const last = seeMessages.value[idx]
    if (last.phase === 'generating' || last.phase === 'initializing') {
      seeMessages.value[idx].content = buffer
      scrollToBottom()
    } else {
      seeMessages.value.push({ agent: '后富', phase: 'generating', content: buffer, timestamp: Date.now() })
      scrollToBottom()
    }
  } else {
    addSeeMessage('后富', 'generating', buffer)
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
</script>

<template>
<WorkflowStepBase
  :project-id="projectId"
  :step-number="5"
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
.step5-see-messages { max-height: 500px; overflow-y: auto; padding: 8px; }
.step5-see-empty { padding: 32px; text-align: center; color: #909399; font-size: 14px; }
.step5-see-msg {
  padding: 8px 12px; margin-bottom: 4px; border-radius: 6px;
  &.generating { background: #fff7ed; }
  &.qa_inspecting { background: #eff6ff; }
  &.qa_passed { background: #f0fdf4; }
  &.qa_failed { background: #fef2f2; }
  &.error { background: #fef2f2; }
  &.done { background: #f0fdf4; font-weight: 500; }
  &.initializing { background: #f9fafb; }
  &.timing { background: #fefce8; border-left: 3px solid #eab308; }
}
.step5-see-msg-header {
  display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 12px;
}
.step5-see-msg-avatar { font-size: 14px; width: 20px; text-align: center; }
.step5-see-msg-agent { font-weight: 600; color: #303133; }
.step5-see-msg-time { color: #909399; margin-left: auto; font-size: 11px; }
.step5-see-msg-body { font-size: 13px; color: #606266; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
</style>
