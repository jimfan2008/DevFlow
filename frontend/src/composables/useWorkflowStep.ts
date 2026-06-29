import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { workflowApi } from '@/api/modules/workflow'

export type StepStatus = 'pending' | 'in_progress' | 'qa_review' | 'completed' | 'rejected' | 'error'

export interface UseWorkflowStepOptions {
  projectId: string
  stepNumber: number
  autoLoad?: boolean
}

export function useWorkflowStep({ projectId, stepNumber, autoLoad = true }: UseWorkflowStepOptions) {
  const route = useRoute()
  const router = useRouter()

  const projectName = ref('')
  const loading = ref(false)
  const executing = ref(false)
  const error = ref('')
  const stageLog = ref<{ type: string; message: string }[]>([])
  const liveContent = ref('')
  const streamStatus = ref('')
  const haimeiPrompt = ref('')
  const showPrompt = ref(false)
  const wsTimer = ref<ReturnType<typeof setTimeout> | null>(null)
  let ws: WebSocket | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null

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

  function getProgressWsUrl(): string {
    const token = localStorage.getItem('access_token') || ''
    const port = import.meta.env.VITE_BACKEND_PORT || '9000'
    const base = import.meta.env.VITE_WS_BASE_URL || `ws://${location.hostname}:${port}`
    return `${base}/api/step${stepNumber}/progress/${projectId}?token=${encodeURIComponent(token)}`
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

  function clearAllTimers() {
    if (wsTimer.value) { clearTimeout(wsTimer.value); wsTimer.value = null }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
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
            stageLog.value.push({ type: msg.type, message: msg.message || '' })
            if (msg.content) {
              liveContent.value += msg.content
            }
          } else if (msg.type === 'content') {
            liveContent.value += msg.content
          } else if (msg.type === 'prompt') {
            haimeiPrompt.value = msg.prompt || ''
            showPrompt.value = true
            stageLog.value.push({ type: 'progress', message: `📝 已生成海梅提示词（第${msg.round || 1}轮）` })
          } else if (msg.type === 'done') {
            stageLog.value.push({ type: 'done', message: msg.message })
            streamStatus.value = msg.message
            clearAllTimers()
            setTimeout(() => {
              loadStatus().then(() => {
                const nextStepNum = stepNumber + 1
                if (nextStepNum <= 16) {
                  router.push({ name: `Step${nextStepNum}`, params: { projectId }, query: { name: projectName.value } })
                }
              })
            }, 2000)
          } else if (msg.type === 'error') {
            stageLog.value.push({ type: 'error', message: msg.message })
            clearAllTimers()
            executing.value = false
          }
        } catch {}
      }
      ws.onclose = () => { ws = null }
      ws.onerror = () => { ws = null }
    } catch {}
  }

  function startPolling(onPollComplete?: () => void) {
    pollTimer = setInterval(async () => {
      try {
        const res = await workflowApi.getStatus(projectId) as any
        const data = res?.data || res
        const stepKey = String(stepNumber)
        const prevStepKey = String(prevStep.value)
        const stepRow = data?.steps?.[stepKey]
        const prevRow = data?.steps?.[prevStepKey]

        if (stepRow?.status === 'completed' || stepRow?.status === 'qa_review') {
          clearAllTimers()
          if (onPollComplete) {
            await onPollComplete()
          } else {
            await loadStatus()
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
      const res = await workflowApi.getStatus(projectId) as any
      const data = res?.data || res
      const steps = data?.steps || {}
      const stepKey = String(stepNumber)
      const stepRow = steps[stepKey] || {}

      stepStatus.value = stepRow.status || 'pending'

      const artKeyName = `step${stepNumber}`
      const artifacts: any = (data as any)?.[artKeyName] || {}

      // 安全网：状态为 qa_review 但产物已标记 qa_passed，视为已完成（步骤6-14内部QA已通过）
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

      if (stepStatus.value === 'completed') {
        const nextStepNum = stepNumber + 1
        if (nextStepNum <= 16) {
          clearAllTimers()
          setTimeout(() => {
            router.push({ name: `Step${nextStepNum}`, params: { projectId }, query: { name: projectName.value } })
          }, 2000)
          return
        }
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
        connectWs()
        startPolling()
        resetStuckTimer()
      }
    } catch (e: any) {
      error.value = e?.message || '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function handleExecute() {
    executing.value = true
    error.value = ''
    stageLog.value = []
    stageLog.value.push({ type: 'stage', message: `🚀 正在启动步骤${stepNumber}...` })

    if (stepNumber >= 6 && stepNumber <= 14) {
      // Connect WS BEFORE execute to avoid missing initial broadcasts
      connectWs()
      startPolling()
      resetStuckTimer()

      try {
        const res = await workflowApi.executeStep(projectId, stepNumber)
        const data = res?.data || res

        // 等待片刻后检查状态
        await new Promise(r => setTimeout(r, 1000))
        let retries = 3
        let stepRow: any
        while (retries > 0) {
          const statusRes = await workflowApi.getStatus(projectId) as any
          const statusData = statusRes?.data || statusRes
          stepRow = statusData?.steps?.[String(stepNumber)]
          if (stepRow?.status !== 'pending') break
          retries--
          if (retries > 0) await new Promise(r => setTimeout(r, 1000))
        }

        if (stepRow?.status === 'in_progress') {
          executing.value = false
          ElMessage.success(`步骤${stepNumber}已启动`)
          stepStatus.value = 'in_progress'
          streamStatus.value = '🚀 正在执行...'
        } else if (stepRow?.status === 'completed' || stepRow?.status === 'qa_review') {
          executing.value = false
          ElMessage.success(`步骤${stepNumber}已完成`)
          await loadStatus()
        } else {
          executing.value = false
          error.value = `推进失败：步骤状态为"${stepRow?.status}"，请稍后重试`
        }
      } catch (e: any) {
        executing.value = false
        error.value = e?.message || '与后端通信失败'
      }
      return
    }

    try {
      const res = await workflowApi.haimeiAutoAdvance(projectId)
      const data = res?.data || res

      const statusRes = await workflowApi.getStatus(projectId) as any
      const statusData = statusRes?.data || statusRes
      const stepRow = statusData?.steps?.[String(stepNumber)]

      if (stepRow?.status === 'in_progress') {
        executing.value = false
        ElMessage.success(`步骤${stepNumber}已启动`)
        stepStatus.value = 'in_progress'
        streamStatus.value = '🚀 正在执行...'
        connectWs()
        startPolling()
        resetStuckTimer()
      } else if (stepRow?.status === 'completed' || stepRow?.status === 'qa_review') {
        executing.value = false
        ElMessage.success(`步骤${stepNumber}已完成`)
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

  function handleGoPrev() {
    if (prevStep.value >= 2) {
      router.push({ name: `Step${prevStep.value}`, params: { projectId }, query: { name: projectName.value } })
    }
  }

  function handleGoNext() {
    if (nextStep.value <= 16) {
      router.push({ name: `Step${nextStep.value}`, params: { projectId }, query: { name: projectName.value } })
    }
  }

  function goBack() {
    router.push({ name: 'ProjectDetail', params: { projectId } })
  }

  onMounted(() => { if (autoLoad) loadStatus() })
  onUnmounted(() => {
    clearAllTimers()
    if (ws) { ws.onclose = null; ws.close(); ws = null }
  })

  return {
    projectName,
    loading,
    executing,
    error,
    stageLog,
    liveContent,
    streamStatus,
    haimeiPrompt,
    showPrompt,
    stepStatus,
    ws,
    prevStep,
    nextStep,
    stepName,
    stepNames,
    statusLabelMap,
    statusTagType,
    loadStatus,
    connectWs,
    startPolling,
    resetStuckTimer,
    clearAllTimers,
    handleExecute,
    handleGoPrev,
    handleGoNext,
    goBack,
    setWs: (newWs: WebSocket | null) => { ws = newWs },
  }
}
